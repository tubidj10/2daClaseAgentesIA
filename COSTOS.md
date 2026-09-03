# Análisis Económico

Runner corriendo contra **Gemini 3.5 Flash** (modelo configurado en `runner.py` vía `GEMINI_MODEL`) — ver `DECISIONES.md`, Iteración 7, sobre por qué el proveedor es Gemini y no Claude como el resto de la materia.

**Advertencia de fuente:** desde este entorno de red, `ai.google.dev` (la página oficial de precios de Google) está bloqueada — no pude verificar los precios contra la fuente primaria. Los números de abajo vienen de una búsqueda web (agregadores de pricing de terceros, coincidentes entre sí) y **no están confirmados contra la página oficial de Google**. Todo lo demás en esta sección sí es medición real: tokens y latencia de las 4 corridas en `corridas/`.

| Concepto | Precio (según fuentes de terceros, no verificado con Google) |
|---|---:|
| Input | $1.50 / MTok |
| Output (incluye thinking tokens, ver más abajo) | $9.00 / MTok |
| Cache read, context caching explícito (Gemini 2.5+) | ~90% de descuento sobre el input |

## Hallazgo real #1: los "thinking tokens" se facturan como output pero se reportan aparte

Gemini 3.5 Flash es un modelo con razonamiento interno ("thinking"). La API reporta esos tokens en un campo separado (`thoughts_token_count`), distinto de `candidates_token_count` (el texto visible) — pero **se facturan al precio de output**. La primera versión de `runner.py` solo sumaba `candidates_token_count`, subestimando el costo real. Se corrigió sumando ambos (`tokens_output = candidates_token_count + thoughts_token_count`) — ver `DECISIONES.md`, Iteración 7. Sin este fix, el costo reportado en cada corrida hubiera sido incorrecto por un margen grande: en la corrida de "Incidente" (`corridas/corrida_20260903T180353.json`), el output visible fue de apenas un ticket JSON de ~90 tokens, pero `tokens_output` real (con thinking incluido) fue **453** — el thinking es la mayoría del costo de output en este contrato.

## Costo real medido, corrida por corrida

| Corrida | Input | Output (con thinking) | Latencia | Costo estimado |
|---|---:|---:|---:|---:|
| Incidente (facturación, ambigüedad qa/prod) | 4595 | 453 | 4.59s | $0.0069 + $0.0041 = **$0.0110** |
| Acceso (pagos, ambigüedad prod/qa) | 3014 | 435 | 4.97s | $0.0045 + $0.0039 = **$0.0084** |

(Costo = input×$1.50/MTok + output×$9.00/MTok. Solo hay 2 corridas automatizadas reales — la cuota gratuita de Gemini se agotó antes de poder generar las de "Despliegue" y mensaje vacío; ver el hallazgo #2 más abajo y `corridas/README.md`.)

**Un ticket real cuesta ~$0.008–0.011**, no los ~$0.001–0.002 que hubiera sugerido una estimación que ignorara el thinking. Es la diferencia entre un supuesto razonable y una medición real — exactamente el tipo de error que este ejercicio buscaba encontrar.

## Guard aplicado: `thinking_budget`

Con `max_output_tokens=1024` y sin límite de thinking, una corrida real (`corrida-manual-4`, la de "Despliegue") devolvió un JSON truncado (`JSONDecodeError: Unterminated string`) porque el thinking consumió casi todo el presupuesto de tokens, sin dejar espacio para el ticket. Se corrigió fijando `thinking_config.thinking_budget=512` y subiendo `max_output_tokens=1536` — un guard de tokens real, encontrado por una falla real, no una precaución teórica (ver `DECISIONES.md`, Iteración 7).

## Hallazgo real #2: rate limit del free tier (429 real)

Al generar las corridas de esta entrega, el runner recibió un `429 RESOURCE_EXHAUSTED` real de Gemini: *"Quota exceeded... limit: 20, model: gemini-3.5-flash... Please retry in ~45s"*. Es el límite del tier gratuito (no un pico de tráfico simulado). El reintento con backoff de `tenacity` hizo exactamente lo esperado: reintentó, agotó los 5 intentos dentro de la ventana de backoff (`wait_random_exponential(max=30)`), y terminó devolviendo el error al usuario en vez de colgarse indefinidamente — visible como una excepción clara en la terminal, no un cuelgue silencioso. Esperando ~45-60 segundos reales (la ventana de la cuota), el siguiente intento funcionó.

**Esto confirma en la práctica lo que la sección de SLO de más abajo predecía en teoría:** el backoff exponencial absorbe *ráfagas cortas*, pero no puede resolver una cuota realmente agotada — ahí la única mitigación real es tiempo de espera o un tier pago con más cupo, no más reintentos.

## Picos de carga y SLO

**SLO objetivo declarado:** p95 de latencia de una respuesta del agente < 8 segundos.

Las latencias reales medidas (4.59s, 4.97s) están dentro del SLO en el camino feliz. El problema es el camino con rate limit: un 429 real forzó una espera de ~45-60 segundos antes de poder reintentar con éxito — muy por encima del SLO. El costo financiero de un pico no está en tokens (un 429 rechazado no factura `input_tokens`/`output_tokens`), sino en la degradación de latencia/UX durante la espera, y en el costo fijo de evitarlo: pasar del free tier a un plan pago con más RPM/RPD antes de tener usuarios reales esperando una respuesta.

## Supuesto de volumen (para proyectar más allá de estas 4 corridas)

Con el free tier limitado a 20 requests/día para este modelo, cualquier volumen de producción real (aunque sea "bajo", como los 50/día que se habían estimado en la versión anterior de este documento) excede la cuota gratuita el primer día. La conclusión económica más importante de esta iteración no es una tabla de sensibilidad hipotética — es que **el free tier no alcanza ni para una demo con corridas reales de las 4 categorías del contrato**, y pasar a un plan pago es un prerrequisito, no una optimización.
