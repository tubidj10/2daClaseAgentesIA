"""Runner del contrato de triage de infraestructura (Entregas 2 y 3, corregido).

Llama a la API de Gemini con la herramienta de inventario real (function
calling), valida el esquema de salida con Pydantic, reintenta ante 429/5xx
con backoff exponencial + jitter, y guarda cada corrida real en corridas/.

Nota de diseño: se usa Gemini (no Claude, como el resto del contrato/costos)
porque es la API key real disponible al momento de esta entrega — ver
DECISIONES.md, Iteración 7. La combinación de function calling + schema de
salida forzado a nivel de protocolo no está confirmada como soportada en la
API de Gemini, así que en vez de asumirla se valida el JSON final con
Pydantic apenas el modelo termina de usar herramientas — el mismo patrón de
"blindaje explícito" que ya usa `prompts/system_prompt.md`.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

load_dotenv()

ROOT = Path(__file__).parent
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
MAX_ITERATIONS = 4             # guard: nunca más de 4 idas y vueltas con herramientas
MAX_OUTPUT_TOKENS = 1536       # guard: cubre thinking_budget + el ticket JSON, sin dejar margen para un ensayo
THINKING_BUDGET = 512          # guard: un ticket de 4 claves no necesita razonar de más
MAX_TOOL_RESULT_CHARS = 4000   # guard: nunca inyectar un resultado de herramienta sin límite


# Enums cerrados, calcados de la pieza 5 (Formato) del contrato — no valores
# libres. Pydantic rechaza cualquier valor fuera de este set con ValidationError.
TipoSolicitud = Literal["Acceso", "Incidente", "Despliegue", "Ajuste de recursos", "Desconocida"]
Entorno = Literal["dev", "qa", "prod", "Desconocido"]


class TicketSchema(BaseModel):
    tipo_solicitud: TipoSolicitud
    entorno: Entorno
    titulo_ticket: str
    datos_faltantes: list[str]


def _parsear_ticket(texto: str) -> TicketSchema:
    """Valida el texto final del modelo contra TicketSchema.

    El schema no se fuerza a nivel de protocolo (function calling +
    response_json_schema no está confirmado como compatible en Gemini), así
    que esta validación es la única línea de defensa a nivel de código sobre
    el output final. `json.loads` va envuelto explícitamente: con
    THINKING_BUDGET mal calibrado, una corrida real devolvió un JSON
    truncado (ver DECISIONES.md, Iteración 7) y el traceback crudo de
    json.loads no decía dónde mirar.
    """
    try:
        payload = json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"El modelo devolvió un JSON inválido o truncado (revisar THINKING_BUDGET/MAX_OUTPUT_TOKENS "
            f"en runner.py). Texto crudo recibido: {texto!r}"
        ) from e
    return TicketSchema.model_validate(payload)


BUSCAR_EN_INVENTARIO_DECLARATION = types.FunctionDeclaration(
    name="buscar_en_inventario",
    description=(
        "Busca un componente en el inventario real de infraestructura y devuelve "
        "las filas que coinciden (entorno, cluster, namespace, pod). Solo lectura."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "componente": {
                "type": "string",
                "description": "Nombre del componente a buscar, tal como aparece en el mensaje del usuario",
            }
        },
        "required": ["componente"],
    },
)

TOOLS = [types.Tool(function_declarations=[BUSCAR_EN_INVENTARIO_DECLARATION])]


def cargar_prompt(nombre: str) -> str:
    return (ROOT / "prompts" / nombre).read_text(encoding="utf-8")


def buscar_en_inventario(componente: str) -> str:
    filas = (ROOT / "inventario_infraestructura.csv").read_text(encoding="utf-8").splitlines()
    coincidencias = [f for f in filas[1:] if componente.lower() in f.lower()]
    resultado = "\n".join(coincidencias) if coincidencias else "sin coincidencias"
    return resultado[:MAX_TOOL_RESULT_CHARS]


def _es_reintentable(exc: BaseException) -> bool:
    return isinstance(exc, genai_errors.APIError) and exc.code in (429, 500, 503)


def _retry_delay_del_servidor(exc: BaseException) -> float | None:
    """Lee el RetryInfo.retryDelay real que Gemini devuelve en un 429/503.

    Encontrado corriendo el runner de verdad: reintentar con backoff genérico
    contra una cuota agotada es contraproducente — cada intento es otra
    request contra la misma cuota, y el backoff exponencial (tope 30s) nunca
    llega a esperar los ~45-60s que el propio servidor pide. Respetar el
    retryDelay real es la corrección (ver DECISIONES.md, Iteración 8).
    """
    if not isinstance(exc, genai_errors.APIError) or not isinstance(exc.details, dict):
        return None
    detalles = exc.details.get("error", {}).get("details", [])
    for d in detalles:
        if isinstance(d, dict) and str(d.get("@type", "")).endswith("RetryInfo"):
            try:
                return float(str(d["retryDelay"]).rstrip("s"))
            except (KeyError, ValueError):
                return None
    return None


def _esperar_ante_reintento(retry_state) -> float:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    delay = _retry_delay_del_servidor(exc) if exc else None
    if delay is not None:
        return delay
    return wait_random_exponential(multiplier=1, max=30)(retry_state)


@retry(
    retry=retry_if_exception(_es_reintentable),
    stop=stop_after_attempt(5),
    wait=_esperar_ante_reintento,
    reraise=True,
)
def llamar_modelo(client: genai.Client, **kwargs):
    return client.models.generate_content(**kwargs)


def ejecutar(mensaje_usuario: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY. Copiá .env.example a .env y completala.")

    client = genai.Client(api_key=api_key)
    system_prompt = cargar_prompt("system_prompt.md")
    user_prompt = cargar_prompt("user_prompt.md").replace("[Insertar mensaje aquí]", mensaje_usuario)
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=TOOLS,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        thinking_config=types.ThinkingConfig(thinking_budget=THINKING_BUDGET),
    )

    tokens_input = tokens_output = 0
    inicio = time.monotonic()
    texto = None

    for _ in range(MAX_ITERATIONS):
        resp = llamar_modelo(client, model=MODEL, contents=contents, config=config)
        if resp.usage_metadata:
            tokens_input += resp.usage_metadata.prompt_token_count or 0
            # Gemini factura los "thinking tokens" a precio de output, pero los
            # reporta separado en thoughts_token_count — hay que sumarlos a mano
            # o el costo real queda subestimado (ver DECISIONES.md, Iteración 7).
            tokens_output += (resp.usage_metadata.candidates_token_count or 0) + (
                resp.usage_metadata.thoughts_token_count or 0
            )

        llamadas = resp.function_calls
        if not llamadas:
            texto = resp.text
            break

        contents.append(resp.candidates[0].content)
        partes_respuesta = []
        for llamada in llamadas:
            if llamada.name == "buscar_en_inventario":
                resultado = buscar_en_inventario(llamada.args["componente"])
                partes_respuesta.append(
                    types.Part.from_function_response(name=llamada.name, response={"result": resultado})
                )
        contents.append(types.Content(role="tool", parts=partes_respuesta))
    else:
        raise RuntimeError(f"Se alcanzó el límite de {MAX_ITERATIONS} iteraciones sin respuesta final.")

    latencia = time.monotonic() - inicio
    ticket = _parsear_ticket(texto)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modelo": MODEL,
        "mensaje_usuario": mensaje_usuario,
        "output": ticket.model_dump(),
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "latencia_segundos": round(latencia, 3),
    }


def main():
    if len(sys.argv) < 2:
        print('Uso: python runner.py "mensaje del usuario"')
        sys.exit(1)

    corrida = ejecutar(sys.argv[1])
    (ROOT / "corridas").mkdir(exist_ok=True)
    nombre = ROOT / "corridas" / f"corrida_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.json"
    nombre.write_text(json.dumps(corrida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(corrida, indent=2, ensure_ascii=False))
    print(f"\nGuardado en {nombre.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
