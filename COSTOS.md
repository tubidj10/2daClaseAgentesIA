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
| Despliegue (frontend, ambigüedad dev/prod) | 3009 | 598 | **82.82s** (incluye espera real de un 429, ver más abajo) | $0.0045 + $0.0054 = **$0.0099** |

(Costo = input×$1.50/MTok + output×$9.00/MTok. Hay 3 corridas automatizadas reales — la cuota gratuita de Gemini se agotó antes de poder generar la de mensaje vacío; ver el hallazgo #2 más abajo y `corridas/README.md`.)

**Un ticket real cuesta ~$0.008–0.011**, no los ~$0.001–0.002 que hubiera sugerido una estimación que ignorara el thinking. Es la diferencia entre un supuesto razonable y una medición real — exactamente el tipo de error que este ejercicio buscaba encontrar.

## Guard aplicado: `thinking_budget`

Con `max_output_tokens=1024` y sin límite de thinking, una corrida real contra el runner devolvió un JSON truncado (`JSONDecodeError: Unterminated string`) porque el thinking consumió casi todo el presupuesto de tokens, sin dejar espacio para el ticket. Se corrigió fijando `thinking_config.thinking_budget=512` y subiendo `max_output_tokens=1536` — un guard de tokens real, encontrado por una falla real, no una precaución teórica (ver `DECISIONES.md`, Iteración 7).

## Hallazgo real #2: rate limit del free tier (429 real), y por qué el backoff genérico no alcanza

Al generar las corridas de esta entrega, el runner recibió varios `429 RESOURCE_EXHAUSTED` reales de Gemini: *"Quota exceeded... limit: 20, model: gemini-3.5-flash... Please retry in ~3-60s"* (el delay pedido por el servidor fluctuó entre intentos, no fue un valor fijo). Es el límite del tier gratuito (no un pico de tráfico simulado).

La primera versión del retry usaba backoff exponencial genérico (`wait_random_exponential(max=30)`): agotaba los 5 intentos sin nunca esperar los ~45-60s reales que el servidor pedía, y cada intento fallido era en sí mismo otra request contra la misma cuota — es decir, **reintentar a ciegas empeoraba la situación en vez de ayudar**. Se corrigió leyendo el `RetryInfo.retryDelay` real del cuerpo del error 429/503 y usándolo como tiempo de espera (`_retry_delay_del_servidor` en `runner.py`, con fallback a backoff exponencial si el servidor no lo informa).

**Resultado medido:** la corrida de "Despliegue" (arriba) esperó el delay real del servidor y tardó **82.8 segundos** en total, pero terminó con éxito — contra los 5 intentos fallidos y ~150s desperdiciados de las corridas anteriores a este fix. Es una mejora real de resiliencia, verificada contra la API, no una suposición sobre cómo "debería" comportarse un backoff.

## Picos de carga y SLO

**SLO objetivo declarado:** p95 de latencia de una respuesta del agente < 8 segundos.

Las latencias reales medidas en el camino feliz (4.59s, 4.97s) están dentro del SLO. El problema es el camino con rate limit: la corrida de "Despliegue" tardó **82.8 segundos** de punta a punta por esperar un 429 real — muy por encima del SLO, aunque terminó con éxito gracias al fix del `retryDelay`. El costo financiero de un pico no está en tokens (un 429 rechazado no factura `input_tokens`/`output_tokens`), sino en la degradación de latencia/UX durante la espera, y en el costo fijo de evitarlo: pasar del free tier a un plan pago con más RPM/RPD antes de tener usuarios reales esperando una respuesta.

## Elección de modelo: el más chico que hace bien la tarea

El criterio del curso es explícito: usar el modelo más chico que resuelve bien la tarea, no el más grande disponible. `gemini-3.5-flash` no es el modelo más barato de la familia Gemini — existe `gemini-3.5-flash-lite`, con precios varias veces menores. Antes de asumir que Flash era la elección correcta, se probó Flash-Lite contra el mismo caso real (ambigüedad qa/prod de facturación) que ya tenía una corrida documentada en Flash.

**Lo que pasó, probado en vivo, dos veces con el mismo input:**
- Primera llamada: Flash-Lite **no llamó a la herramienta** — devolvió directamente `{"entorno": "Desconocido", "datos_faltantes": ["Entorno (dev/qa/prod)", "Nombre exacto del componente o pod"]}`, la misma pregunta genérica y a ciegas que el contrato tenía *antes* de la Entrega 3 (Iteración 3). El costo fue más bajo (2913 tokens de input, 89 de output) precisamente porque se saltó el paso que le da valor al contrato.
- Segunda llamada, mismo input exacto: Flash-Lite **sí** generó el `function_call` para `buscar_en_inventario` — inconsistente entre corridas idénticas.

**Conclusión:** Flash-Lite es más barato, pero no confiable para lo que este contrato necesita — que el modelo consulte la herramienta *antes* de completar `entorno`, siempre, no a veces. `gemini-3.5-flash` sí lo hizo consistentemente en las 3 corridas automatizadas reales de este repo (`corridas/*.json`). Bajar a Flash-Lite para ahorrar reintroduciría exactamente el problema que la Entrega 3 resolvió. Esto no es una preferencia — es el resultado de una prueba real, documentada, no una suposición sobre qué modelo "debería" alcanzar.

No se probó `gemini-3.5-pro` (o equivalente) porque Flash ya cumple la tarea de forma consistente y confiable en las corridas reales disponibles; subir de tier no tiene justificación sin una falla real que lo pida — el mismo criterio de "el más chico que alcanza", aplicado en la otra dirección.

## Proyección semanal y anual (con el costo real medido, no estimado)

Costo real promedio por corrida, medido en las 3 corridas automatizadas de `corridas/`: ($0.0110 + $0.0084 + $0.0099) / 3 ≈ **$0.0098/corrida**.

Supuesto de volumen declarado (no medido — es la escala razonable para un equipo de IT chico usando esto como triage de pedidos por chat): 30 solicitudes/día hábil.

| Período | Solicitudes | Costo estimado (a $0.0098/corrida real) |
|---|---:|---:|
| Semanal (5 días hábiles) | 150 | **≈ $1.47** |
| Anual (260 días hábiles) | 7.800 | **≈ $76.44** |

Es un sistema barato de operar a esta escala — el costo real medido (con thinking incluido) sigue siendo órdenes de magnitud menor que el tiempo de un SRE humano respondiendo estos mismos mensajes uno por uno. El obstáculo real no es el costo por corrida: es que el **free tier** (usado para todas las corridas de este repo) no soporta ni por asomo este volumen — hace falta un plan pago con más RPM/RPD antes de operar a 30/día real, aunque el costo en dólares sea bajo (ver el hallazgo #2 más abajo).

## Supuesto de volumen — límite real del free tier

Con el free tier limitado a 20 requests/día para este modelo, cualquier volumen de producción real (incluida la proyección de 30/día de arriba) excede la cuota gratuita el primer día. La conclusión económica más importante de esta iteración no es la tabla de sensibilidad — es que **el free tier no alcanza ni para una demo con corridas reales de las 4 categorías del contrato**, y pasar a un plan pago es un prerrequisito, no una optimización.
