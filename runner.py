"""Runner del contrato de triage de infraestructura (Entregas 2 y 3, corregido).

Llama a la API de Anthropic con la herramienta de inventario real, fuerza el
esquema de salida a nivel de protocolo (output_config.format), reintenta ante
429/5xx con backoff exponencial + jitter, y guarda cada corrida real en
corridas/.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

load_dotenv()

ROOT = Path(__file__).parent
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_ITERATIONS = 4            # guard: nunca más de 4 idas y vueltas con herramientas
MAX_TOKENS = 1024             # guard: la salida es un ticket corto, no un ensayo
MAX_TOOL_RESULT_CHARS = 4000  # guard: nunca inyectar un resultado de herramienta sin límite

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "tipo_solicitud": {
            "type": "string",
            "enum": ["Acceso", "Incidente", "Despliegue", "Ajuste de recursos", "Desconocida"],
        },
        "entorno": {"type": "string", "enum": ["dev", "qa", "prod", "Desconocido"]},
        "titulo_ticket": {"type": "string"},
        "datos_faltantes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tipo_solicitud", "entorno", "titulo_ticket", "datos_faltantes"],
    "additionalProperties": False,
}

TOOLS = [
    {
        "name": "buscar_en_inventario",
        "description": (
            "Busca un componente en el inventario real de infraestructura y devuelve "
            "las filas que coinciden (entorno, cluster, namespace, pod). Solo lectura."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "componente": {
                    "type": "string",
                    "description": "Nombre del componente a buscar, tal como aparece en el mensaje del usuario",
                }
            },
            "required": ["componente"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


class TicketSchema(BaseModel):
    tipo_solicitud: str
    entorno: str
    titulo_ticket: str
    datos_faltantes: list[str]


def cargar_prompt(nombre: str) -> str:
    return (ROOT / "prompts" / nombre).read_text(encoding="utf-8")


def buscar_en_inventario(componente: str) -> str:
    filas = (ROOT / "inventario_infraestructura.csv").read_text(encoding="utf-8").splitlines()
    coincidencias = [f for f in filas[1:] if componente.lower() in f.lower()]
    resultado = "\n".join(coincidencias) if coincidencias else "sin coincidencias"
    return resultado[:MAX_TOOL_RESULT_CHARS]


@retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.InternalServerError)),
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(multiplier=1, max=30),
    reraise=True,
)
def llamar_modelo(client: anthropic.Anthropic, **kwargs):
    return client.messages.create(**kwargs)


def ejecutar(mensaje_usuario: str) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Falta ANTHROPIC_API_KEY. Copiá .env.example a .env y completala.")

    client = anthropic.Anthropic()
    system_prompt = cargar_prompt("system_prompt.md")
    user_prompt = cargar_prompt("user_prompt.md").replace("[Insertar mensaje aquí]", mensaje_usuario)
    messages = [{"role": "user", "content": user_prompt}]
    output_config = {"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}}

    tokens_input = tokens_output = 0
    inicio = time.monotonic()
    texto = None

    for _ in range(MAX_ITERATIONS):
        resp = llamar_modelo(
            client,
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
            output_config=output_config,
        )
        tokens_input += resp.usage.input_tokens
        tokens_output += resp.usage.output_tokens

        if resp.stop_reason != "tool_use":
            texto = next(b.text for b in resp.content if b.type == "text")
            break

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for bloque in resp.content:
            if bloque.type == "tool_use" and bloque.name == "buscar_en_inventario":
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": buscar_en_inventario(bloque.input["componente"]),
                    }
                )
        messages.append({"role": "user", "content": tool_results})
    else:
        raise RuntimeError(f"Se alcanzó el límite de {MAX_ITERATIONS} iteraciones sin respuesta final.")

    latencia = time.monotonic() - inicio
    # output_config.format ya garantiza JSON válido contra OUTPUT_SCHEMA a nivel de
    # protocolo; esta segunda validación con Pydantic es una capa extra de blindaje.
    ticket = TicketSchema.model_validate(json.loads(texto))

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
