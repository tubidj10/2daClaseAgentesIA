# Triage de Infraestructura — Contrato + Herramienta

Agente de triage: convierte pedidos informales de desarrolladores en tickets estructurados (JSON), consultando un inventario real de infraestructura antes de adivinar nada. Trabajo individual — Martín Pérez — para la materia Programación de y con Agentes de IA (MADE/MBA UCEMA).

## Estructura del repo

| Ruta | Qué es |
|---|---|
| `prompts/system_prompt.md` | Rol, restricciones, formato (schema + auto-validación) y la herramienta — piezas 1, 4, 5, 7 del contrato. |
| `prompts/user_prompt.md` | Contexto, tarea y ejemplos few-shot — piezas 2, 3, 6. Incluye la cláusula anti-inyección sobre el mensaje del usuario. |
| `inventario_infraestructura.csv` | La herramienta: inventario real de componentes (`componente, entorno, cluster, namespace, pod_o_recurso`) que el agente consulta antes de completar `entorno`/`datos_faltantes`. |
| `runner.py` | Runner en Python: llama a la API de Gemini con tool-calling real, valida el schema de salida con Pydantic, reintenta ante 429/5xx con backoff+jitter, y guarda cada corrida en `corridas/`. |
| `run.sh` | Comando único de ejecución: instala dependencias y corre `runner.py`. |
| `tests/test_runner.py` | Tests con `pytest` de la lógica que no depende de la API (búsqueda en inventario, validación de schema). |
| `corridas/` | Corridas reales — manuales (chat) y automatizadas (`runner.py`). Ver `corridas/README.md`. |
| `DECISIONES.md` | Historial de fallas encontradas, cambios aplicados y el commit exacto de cada iteración. |
| `GOBERNANZA.md` | Matriz de autonomía L0–L4, alcance negativo y salvaguardas human-in-the-loop. |
| `COSTOS.md` | Análisis económico con precios de Gemini 3.5 Flash, sensibilidad de context caching y el impacto de picos de carga sobre el SLO. |

## Cómo correr una corrida real

Una sola vez (es una credencial secreta, no se automatiza — ver `DECISIONES.md`, Iteración 6):

```bash
cp .env.example .env   # completar GEMINI_API_KEY
```

Después, un solo comando instala dependencias y corre el runner:

```bash
./run.sh "El pod del microservicio de facturación está reiniciándose en loop."
```

El resultado se imprime en pantalla y queda guardado en `corridas/corrida_<timestamp>.json` con tokens y latencia reales. Ya hay 3 corridas automatizadas reales en `corridas/` (más 7 corridas manuales que cubren camino feliz, ambigüedad y casos sin match en el inventario) — la cuarta categoría quedó pendiente porque se agotó la cuota gratuita de Gemini generándolas; ver `corridas/README.md`.

**Nota:** el runner usa **Gemini**, no Claude — es la API key real disponible al momento de esta entrega (ver `DECISIONES.md`, Iteración 7). El resto del contrato (prompts, gobernanza) es agnóstico al proveedor; `COSTOS.md` está recalculado con precios de Gemini.

Para correr los tests (no requieren API key):

```bash
pytest
```

## Costo por corrida (resumen — detalle completo en `COSTOS.md`)

**Fórmula:** `costo = tokens_input × $1.50/1M + tokens_output × $9.00/1M` (Gemini 3.5 Flash; `tokens_output` incluye los "thinking tokens", que se facturan como output aunque la API los reporta aparte — ver `COSTOS.md`, hallazgo #1).

**Rango real medido**, sobre las 3 corridas automatizadas en `corridas/` (no una estimación — son las 3 corridas reales que existen hoy en el repo):

| | Tokens in | Tokens out | Costo |
|---|---:|---:|---:|
| Mínimo (Acceso) | 3.014 | 435 | **$0.0084** |
| Máximo (Incidente) | 4.595 | 453 | **$0.0110** |
| Promedio (3 corridas) | — | — | **$0.0098** |

Proyectado al volumen declarado en `COSTOS.md` (30 solicitudes/día hábil): **≈ $1.47/semana, ≈ $76.44/año**. Fórmula desagregada, elección de modelo justificada contra una alternativa más barata, y el detalle corrida por corrida están en `COSTOS.md`.

## El contrato, en una línea

Un system prompt fijo (rol + restricciones + formato) separado de un user prompt variable (contexto + tarea + ejemplos), con una herramienta de solo lectura en el medio: el agente nunca inventa un entorno, cluster o pod — si el inventario no lo confirma, lo marca como faltante. El detalle de por qué cada pieza quedó así, y qué se rompió antes de llegar a esta versión, está en `DECISIONES.md`.
