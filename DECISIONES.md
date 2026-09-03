# Decisiones e Iteraciones

Historial de las fallas reales encontradas al probar el contrato, el cambio aplicado en cada caso, y el commit exacto donde quedó. Cuando existe una métrica diferencial real (tokens/latencia), se reporta; cuando no, se dice explícitamente que está pendiente en vez de inventarla — ver la nota al final.

## Iteración 1 — Control de entornos asumidos

- **Falla:** al recibir pedidos sin entorno especificado, el modelo asumía que era "Producción", lo cual es un riesgo crítico.
- **Cambio aplicado:** se agregó a la pieza 4 (Restricciones): *"Prohibido asumir que el entorno es 'Producción' salvo que el usuario lo indique textualmente."*
- **Resultado:** el agente empezó a clasificar los entornos no mencionados como "Desconocido" y a exigir el dato.
- **Commit:** incluida en [`832a7289c382d55b4f3179048e1e3ef72947d9c8`](https://github.com/tubidj10/2daClaseAgentesIA/commit/832a7289c382d55b4f3179048e1e3ef72947d9c8) (versión base de la Entrega 2, ya con las iteraciones 1 y 2 aplicadas).

## Iteración 2 — Consistencia del esquema JSON

- **Falla:** en pedidos completos, el modelo omitía la clave `datos_faltantes` del JSON, rompiendo la estructura esperada para lectura automatizada.
- **Cambio aplicado:** se ajustó la pieza 5 (Formato): *"El array 'datos_faltantes' debe existir siempre; si no falta nada, devuélvelo como []."*
- **Resultado:** output 100% predecible y estructurado.
- **Commit:** [`832a7289c382d55b4f3179048e1e3ef72947d9c8`](https://github.com/tubidj10/2daClaseAgentesIA/commit/832a7289c382d55b4f3179048e1e3ef72947d9c8).

## Iteración 2.1 — Hallazgo de entrada vacía

- **Falla:** al correr el contrato dos veces sin ningún mensaje para procesar, el modelo devolvió dos estructuras JSON completamente distintas entre sí (claves diferentes, valores por defecto diferentes), rompiendo la repetibilidad en el caso borde de entrada vacía.
- **Cambio aplicado:** se agregó a la pieza 5 la definición explícita y cerrada de las cuatro claves obligatorias, sus valores permitidos, y el output exacto a devolver cuando no hay mensaje para procesar.
- **Resultado:** se corrió nuevamente el caso de mensaje vacío contra el contrato corregido (en otro modelo, Gemini, para validar portabilidad) y el output coincidió exactamente con el default definido en la pieza 5.
- **Commit:** [`832a7289c382d55b4f3179048e1e3ef72947d9c8`](https://github.com/tubidj10/2daClaseAgentesIA/commit/832a7289c382d55b4f3179048e1e3ef72947d9c8).

## Iteración 3 — Herramienta real (Entrega 3)

- **Motivación:** el contrato solo procesaba texto que un humano le pegaba; no tenía forma de verificar nada contra la realidad.
- **Cambio aplicado:** se agregó la pieza 7 (Herramienta): consultar `inventario_infraestructura.csv` (inventario real de componentes) antes de completar `entorno` y `datos_faltantes`.
- **Resultado:** corrida real documentada en `corridas/corrida-manual-4-entrega3-herramienta.md`. El caso de prueba (componente "Facturación") reveló una ambigüedad real — existe en `qa` y en `prod` — y el contrato la manejó bien: no asumió un entorno, pero reemplazó 3 preguntas genéricas por 1 pregunta puntual con las dos opciones reales.
- **Commit:** [`0040ee4f115418aaad9e611c1ce90c2acb7ad656`](https://github.com/tubidj10/2daClaseAgentesIA/commit/0040ee4f115418aaad9e611c1ce90c2acb7ad656).

## Iteración 4 — Validación JSON (corrección post-entrega del profesor)

- **Feedback recibido:** *"Excelente foco en casos borde y estructura exhaustiva. El hallazgo de entrada vacía es especialmente valioso. Agregá una validación JSON..."*
- **Cambio aplicado:** se agregó a la pieza 5 una instrucción explícita de auto-validación sintáctica antes de responder (comillas dobles, sin comas colgantes, llaves balanceadas, exactamente las cuatro claves).
- **Commit:** [`5d247c980d9fa38ea865524f2006121fff9ae0cc`](https://github.com/tubidj10/2daClaseAgentesIA/commit/5d247c980d9fa38ea865524f2006121fff9ae0cc).

## Iteración 5 — Schema forzado a nivel de protocolo, gobernanza y reproducibilidad

- **Motivación:** la Iteración 4 resuelve la validación JSON *a nivel de prompt* (el modelo se autochequea, pero nada externo lo garantiza). Un runner real puede hacerlo mejor.
- **Cambio aplicado:**
  - `runner.py` fuerza el esquema de salida con `output_config.format` (JSON Schema) en la propia llamada a la API — una respuesta que no cierre el esquema no puede llegar como texto libre; es una garantía de protocolo, no una instrucción que el modelo podría ignorar.
  - Reintentos con backoff exponencial + jitter (`tenacity`) ante `RateLimitError` (429) e `InternalServerError` (5xx/529).
  - Guards explícitos: `MAX_ITERATIONS` (tope de idas y vueltas con la herramienta) y `MAX_TOKENS` / `MAX_TOOL_RESULT_CHARS` (tope de gasto y de inyección de datos externos).
  - `buscar_en_inventario` pasó de ser una consulta manual (`grep` desde el chat) a una tool real de la API (`tools=[...]`, `strict: true`), invocada por el propio modelo.
  - Cláusula anti-inyección en `prompts/user_prompt.md`: el mensaje del usuario se marca explícitamente como dato, no instrucción.
  - Gobernanza y alcance documentados en `GOBERNANZA.md` (matriz L0-L4, alcance negativo, salvaguardas humanas).
  - Análisis económico con precios reales de Claude Sonnet 5 en `COSTOS.md`.
  - Tests automatizados (`tests/test_runner.py`, `pytest`) sobre la lógica que no depende de la API: búsqueda en inventario y validación de schema.
- **Commit:** [`c1274356acdbd7c303c928161aa5a39b0b26663b`](https://github.com/tubidj10/2daClaseAgentesIA/commit/c1274356acdbd7c303c928161aa5a39b0b26663b).

## Iteración 6 — Trazabilidad de commits y comando único de ejecución

- **Motivación:** cerrar los dos últimos puntos señalados por la auditoría automática: (a) los commits de `DECISIONES.md` estaban abreviados (7 caracteres) en vez del hash completo; (b) faltaba un comando único que instale, configure y corra el runner sin pasos manuales dispersos por el README.
- **Cambio aplicado:**
  - Se reemplazaron todos los hashes abreviados de este archivo por el SHA completo de 40 caracteres, enlazado al commit real en GitHub.
  - Se agregó `run.sh`, que encadena `pip install -r requirements.txt` y `python runner.py "$1"` en un solo comando (`./run.sh "mensaje"`).
- **Límite honesto que no se puede automatizar:** el único paso manual que queda es completar la API key en `.env` la primera vez. Eso no es una falla de reproducibilidad — es una credencial secreta que, por diseño, nunca puede ni debe quedar en un comando o script versionado (ver `GOBERNANZA.md` e `Higiene de Secretos` en el informe forense). Automatizarlo significaría hardcodear una API key en el repo, exactamente lo que la propia auditoría marca como riesgo si lo encontrara.
- **Commit:** [`c37085a8b2aeb48f4e3cd3a1c465e7e5a912ecde`](https://github.com/tubidj10/2daClaseAgentesIA/commit/c37085a8b2aeb48f4e3cd3a1c465e7e5a912ecde).

## Iteración 7 — Migración a Gemini y corridas automatizadas reales

- **Motivación:** se consiguió una API key real, pero de **Gemini**, no de Anthropic. En vez de dejar el runner sin usar, se adaptó a la API que sí había disponible.
- **Cambios aplicados, en el orden en que surgieron (cada uno por una falla real, no anticipada):**
  1. `runner.py` reescrito con `google-genai` (cliente, `FunctionDeclaration`/`Tool` para la herramienta, loop manual de function calling). Las firmas exactas del SDK (`Part.from_text(text=...)` es keyword-only, campos válidos de `GenerateContentConfig`, etc.) se verificaron por introspección del paquete instalado en vez de asumirlas — un primer intento con `Part.from_text(user_prompt)` posicional falló en la práctica (`TypeError`).
  2. La combinación de function calling + schema de salida forzado a nivel de protocolo (como se hacía con `output_config.format` de Anthropic) no está confirmada como soportada en Gemini, así que se optó por el camino verificable: loop de herramientas + validación del JSON final con Pydantic (ya documentado como "segunda línea de defensa" en `prompts/system_prompt.md`).
  3. **Hallazgo real de facturación:** Gemini 3.5 Flash factura los "thinking tokens" al precio de output, pero la API los reporta separados (`thoughts_token_count`, no incluido en `candidates_token_count`). La primera versión del runner no los sumaba — subestimaba el costo real. Corregido sumando ambos campos.
  4. **Bug real encontrado corriendo el runner:** con `max_output_tokens=1024` y sin límite de thinking, una corrida real devolvió `JSONDecodeError: Unterminated string` — el thinking consumió el presupuesto de tokens sin dejar espacio para el ticket. Corregido fijando `thinking_config.thinking_budget=512` y subiendo `max_output_tokens=1536`. Es el guard de tokens que pedía la auditoría, motivado por una falla real y no por una precaución teórica.
  5. **Rate limit real:** al generar las corridas, el runner recibió un `429 RESOURCE_EXHAUSTED` genuino de Gemini (cuota free-tier de 20 requests/día para este modelo). El retry con backoff de `tenacity` reintentó como estaba diseñado y devolvió el error de forma clara al agotar los intentos — comportamiento correcto ante una cuota realmente agotada, no un fallo del código. Ver `COSTOS.md`.
- **Resultado:** 2 corridas automatizadas reales en `corridas/` (Incidente y Acceso, ambas con ambigüedad real qa/prod detectada por la herramienta) con tokens y latencia genuinos. Las corridas de Despliegue y mensaje vacío quedaron pendientes por la cuota agotada — no se fabricó un resultado para completarlas (ver `corridas/README.md`).
- **COSTOS.md** se recalculó con precios de Gemini (no verificados contra la fuente oficial de Google, bloqueada en este entorno de red — declarado explícitamente) y con los costos reales medidos de las 2 corridas.
- **Commit:** [`1d3d5c1c5d0a86a745f2d76c33f45c0191d65593`](https://github.com/tubidj10/2daClaseAgentesIA/commit/1d3d5c1c5d0a86a745f2d76c33f45c0191d65593).

## Iteración 8 — Enums cerrados en el schema, y por qué NO se agrega un score de confianza

Feedback recibido: *"El contrato solicita JSON pero no restringe todas las categorías a enums cerrados ni incluye scoring de confianza."*

- **Falla real (esta sí se corrigió):** al migrar el runner de Anthropic a Gemini (Iteración 7), `TicketSchema` quedó con `tipo_solicitud: str` y `entorno: str` — una regresión real. La versión original (Anthropic, Iteración 5) sí tenía estos dos campos restringidos a un enum cerrado vía `output_config.format`; al reescribir para Gemini sin ese mecanismo de protocolo, el enum se perdió y Pydantic aceptaba cualquier string.
- **Cambio aplicado:** `tipo_solicitud` y `entorno` ahora son `typing.Literal` con los mismos 5 y 4 valores exactos que ya exigía la pieza 5 del prompt — Pydantic rechaza con `ValidationError` cualquier valor fuera de ese set. Se agregaron dos tests (`test_schema_rechaza_tipo_solicitud_fuera_del_enum`, `test_schema_rechaza_entorno_fuera_del_enum`) que lo prueban.
- **Por qué NO se agrega un "scoring de confianza":** la pieza 5 del contrato (piezas 1-7, Entrega 2) es explícita y deliberada: *"El objeto debe tener exactamente estas cuatro claves, sin agregar ni omitir ninguna"* — una decisión de diseño de la Iteración 2, tomada después de encontrar que un schema ambiguo rompía la repetibilidad (ver Iteración 2.1). Agregar una quinta clave (`confianza` o similar) contradice esa decisión ya validada, y además un score de confianza que el propio modelo se autoasigna no es una medida confiable de nada — no hay una forma barata de verificar que ese número signifique lo que dice significar, a diferencia de los otros cuatro campos, que sí se pueden verificar contra el inventario real. Se prioriza la consistencia del contrato ya probado por sobre seguir una recomendación genérica que no aplica a este caso.
- **Diversidad de escenarios en corridas:** se agregaron 3 corridas manuales nuevas (5, 6 y 7 en `corridas/`) para cubrir camino feliz (`datos_faltantes: []`), componente sin match en el inventario, y alta severidad con entorno declarado explícitamente por el usuario — hasta acá todas las corridas anteriores caían en la misma familia (ambigüedad qa/prod resuelta por la herramienta).
- **Hallazgo real adicional — reintentar contra una cuota agotada empeora las cosas:** generando las corridas automatizadas, `_es_reintentable` reintentaba con backoff exponencial genérico (tope 30s) ante un 429 real, pero el servidor pedía esperas de 3 a 60 segundos que fluctuaban entre intentos — el backoff genérico nunca esperaba lo suficiente, agotaba los 5 intentos, y cada intento fallido era en sí mismo otra request contra la misma cuota ya ajustada. Se corrigió agregando `_retry_delay_del_servidor`, que lee el `RetryInfo.retryDelay` real del cuerpo del error 429/503 y lo usa como tiempo de espera en vez de adivinar con backoff exponencial (con fallback a exponencial si el servidor no lo informa). Probado en vivo: la corrida de "Despliegue" (`corridas/corrida_20260903T182003.json`) esperó el delay real del servidor y tardó **82.8 segundos** en total, pero terminó con éxito en vez de fallar — evidencia real de que respetar el `retryDelay` del proveedor es mejor que backoff exponencial ciego.

## Iteración 9 — Elección de modelo probada, no asumida

- **Motivación:** el criterio del curso para elegir modelo es "el más chico que hace bien la tarea", y hasta esta iteración `gemini-3.5-flash` se usó porque era la key disponible (Iteración 7), no porque se hubiera comprobado que es el más chico adecuado.
- **Prueba real:** se corrió el mismo caso de ambigüedad qa/prod (facturación) contra `gemini-3.5-flash-lite`, el tier inmediato inferior en precio. Resultado: en una de dos llamadas idénticas, el modelo **no llamó a la herramienta** y devolvió `entorno: "Desconocido"` con una pregunta genérica — el mismo comportamiento que el contrato tenía antes de la Entrega 3. En la otra llamada sí la usó. Inconsistente, no confiable.
- **Decisión:** se mantiene `gemini-3.5-flash`, que sí usó la herramienta de forma consistente en las 3 corridas automatizadas reales de este repo. Detalle completo en `COSTOS.md`, sección "Elección de modelo: el más chico que hace bien la tarea".
- **Commit:** [`ef0a28d`](https://github.com/tubidj10/2daClaseAgentesIA/commit/ef0a28dc7cb4938ae0280a336bfcb4d8f4926c1a).

## Tabla de trazabilidad: commit ↔ métrica diferencial

Vínculo explícito entre cada iteración con datos medibles y su commit exacto (las iteraciones puramente de documentación o de rechazo de una sugerencia, como la 2.1 o la mitad de la 8, no tienen métrica porque no cambian código ejecutable):

| Iteración | Commit | Métrica antes → después |
|---|---|---|
| 5 (schema forzado, Anthropic) | [`c127435`](https://github.com/tubidj10/2daClaseAgentesIA/commit/c1274356acdbd7c303c928161aa5a39b0b26663b) | N/A — sin API key todavía, sin corrida real que medir. |
| 6 (comando único) | [`c37085a`](https://github.com/tubidj10/2daClaseAgentesIA/commit/c37085a8b2aeb48f4e3cd3a1c465e7e5a912ecde) | N/A — cambio de tooling, no de comportamiento del modelo. |
| 7 (migración a Gemini + fix de thinking tokens) | [`1d3d5c1`](https://github.com/tubidj10/2daClaseAgentesIA/commit/1d3d5c1c5d0a86a745f2d76c33f45c0191d65593) | Antes del fix de `thoughts_token_count`: `tokens_output` reportado = solo texto visible (ej. ~90-190 tokens). Después: `tokens_output` real = texto + thinking (194→**453**, 163→**435** en las mismas dos corridas, medido en `corridas/*.json`). |
| 8 (enums cerrados + retry consciente de `retryDelay`) | [`7921573`](https://github.com/tubidj10/2daClaseAgentesIA/commit/79215731a2d02916726c210e768aaf879c4f9b6a) | Antes del fix de retry: 5/5 intentos fallidos contra un 429 real, 0 corridas exitosas en esa ventana. Después: la corrida de "Despliegue" (`corrida_20260903T182003.json`) esperó el `retryDelay` real (**82.8s** de latencia total) y terminó con éxito — de 0% a 100% de corridas exitosas ante el mismo tipo de error. |
| 9 (elección de modelo) | [`ef0a28d`](https://github.com/tubidj10/2daClaseAgentesIA/commit/ef0a28dc7cb4938ae0280a336bfcb4d8f4926c1a) | `gemini-3.5-flash-lite`: tool-call detectado en 1 de 2 llamadas idénticas (50% de consistencia). `gemini-3.5-flash`: tool-call detectado en 3 de 3 corridas automatizadas reales (100%). |

## Nota sobre métricas diferenciales (tokens/latencia)

Ya no está pendiente: las 3 corridas automatizadas en `corridas/` traen `tokens_input`, `tokens_output` (incluye thinking) y `latencia_segundos` reales, medidos con una API key real de Gemini — ver el detalle en `COSTOS.md`. No se fabricó ningún número para esta tabla en ningún momento: cuando no había key (Iteraciones 1-6), esta sección decía explícitamente que faltaba, y ahora que sí la hay, muestra las corridas reales en vez de una simulación.
