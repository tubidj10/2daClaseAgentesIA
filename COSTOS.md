# Análisis Económico

Precios reales de Claude Sonnet 5 (modelo configurado en `runner.py` vía `CLAUDE_MODEL`), API directa de Anthropic, vigentes al momento de esta entrega:

| Concepto | Precio |
|---|---:|
| Input | $2.00 / MTok |
| Output | $10.00 / MTok |
| Cache read (~0.1× del input) | $0.20 / MTok |
| Cache write, TTL 5 min (1.25× del input) | $2.50 / MTok |
| Cache write, TTL 1 h (2× del input) | $4.00 / MTok |

No se midieron estos costos contra tráfico real (no hay `ANTHROPIC_API_KEY` disponible aún — ver `DECISIONES.md`), así que todo lo que sigue son estimaciones declaradas a partir del tamaño real de los prompts, no mediciones de `usage` real.

## Supuestos de volumen

- **Prompt fijo (system + user template + definición de la herramienta + schema de salida):** `prompts/system_prompt.md` + `prompts/user_prompt.md` miden 733 palabras en total; con un factor aproximado de 1.3-1.4 tokens/palabra en español, más ~150 tokens de la definición de la herramienta y el JSON Schema de salida, el prefijo fijo **F ≈ 1150 tokens** — por encima del mínimo cacheable de Sonnet 5 (1024 tokens), así que sí puede cachearse.
- **Mensaje variable del usuario:** un pedido informal de chat, **V ≈ 50 tokens** en promedio. Nunca es cacheable (cambia en cada request).
- **Output:** un ticket JSON corto (4 claves), **O ≈ 120 tokens** en promedio.
- **Volumen hipotético:** este contrato usado como servicio real de un equipo de IT chico, en horario de oficina (~9 h/día hábil, 22 días hábiles/mes). Tres escenarios: Bajo (50 pedidos/día), Medio (200/día), Alto (1000/día).

## Costo por request

| | Sin cache | Con cache (lectura, prefijo ya caliente) | Con cache (primera del día, TTL 5 min) |
|---|---:|---:|---:|
| Input fijo (F) | $0.00230 | $0.00023 | $0.00288 (write) |
| Input variable (V) | $0.00010 | $0.00010 | $0.00010 |
| Output (O) | $0.00120 | $0.00120 | $0.00120 |
| **Total** | **$0.00360** | **$0.00153** | **$0.00418** |

Una request que lee un prefijo ya cacheado cuesta ~57% menos que sin cache. La primera request que **escribe** el cache cuesta ~16% *más* que sin cache — cachear solo paga si después hay lecturas suficientes.

## Matriz de sensibilidad: costo mensual con vs. sin Prompt Caching

Tráfico distribuido en ~9h/día hábil ⇒ separación promedio entre requests: Bajo ≈ 11 min, Medio ≈ 2.7 min, Alto ≈ 32 seg.

| Volumen | Requests/día | Sin cache (mensual) | Con cache, TTL correcta (mensual) | Ahorro |
|---|---:|---:|---:|---:|
| Bajo | 50 | $3.96 | $1.78 (TTL 1h) | ~55% |
| Medio | 200 | $15.84 | $6.79 (TTL 5min) | ~57% |
| Alto | 1000 | $79.20 | $33.72 (TTL 5min) | ~57% |

**El hallazgo que importa está en "Bajo": la TTL correcta no es la misma en todos los escenarios.** Con separación promedio de 11 minutos entre pedidos, la TTL de 5 minutos expira *antes* de que llegue el siguiente request — cada uno paga el premium de escritura (1.25×) y nunca llega a leer, lo que da un costo mensual de **$4.59, peor que no cachear en absoluto** ($3.96). Cambiando a TTL de 1 hora (2× en la escritura, pero el prefijo sigue vivo entre pedidos de 11 min) el costo baja a los $1.78 de la tabla — la misma regla que documenta la referencia de pricing: *bajo tráfico disperso con huecos de 5-60 minutos, la TTL de 1 hora es la única ventana donde el 2× se paga solo*. En Medio y Alto, con huecos muy por debajo de 5 minutos, la TTL de 5 minutos ya es la más barata y subir a 1h solo pagaría un premium innecesario.

## Picos de carga y SLO

**SLO objetivo declarado:** p95 de latencia de una respuesta del agente < 8 segundos.

`runner.py` reintenta con `tenacity` ante `RateLimitError` (429) e `InternalServerError` (5xx/529): `stop_after_attempt(5)`, espera exponencial con jitter (`wait_random_exponential(multiplier=1, max=30)`). Eso protege la *disponibilidad* (la corrida eventualmente termina en vez de fallar en el primer 429), pero no protege el SLO de latencia: en el peor caso, varios reintentos cerca del tope de 30 segundos pueden acumular más de un minuto de espera antes de una respuesta exitosa — muy por encima de los 8 segundos objetivo.

**Impacto financiero de un pico:** un 429 rechazado no consume tokens (no hay `input_tokens`/`output_tokens` que facturar en una respuesta de error), así que un pico de carga no dispara un costo variable directo. El costo real de un pico está en dos lugares: (1) la degradación de latencia/UX mientras el backoff absorbe el exceso de tráfico, y (2) el costo fijo de mitigarlo *antes* de que ocurra — pedir un tier de rate limit más alto a Anthropic, o agregar una cola/throttle del lado del cliente para no depender solo de reintentos. Reintentar más agresivamente (subir `stop_after_attempt`) no es gratis: cada intento adicional sigue sin costar tokens, pero sí sigue empujando la latencia p95 en la dirección equivocada — la mitigación correcta ante un pico sostenido es capacidad (tier de rate limit), no más reintentos.
