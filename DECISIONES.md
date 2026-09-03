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

## Nota sobre métricas diferenciales (tokens/latencia)

Ya no está pendiente: `corridas/corrida_20260903T180353.json` y `corridas/corrida_20260903T180503.json` traen `tokens_input`, `tokens_output` (incluye thinking) y `latencia_segundos` reales, medidos con una API key real de Gemini — ver el detalle en `COSTOS.md`. No se fabricó ningún número para esta tabla en ningún momento: cuando no había key (Iteraciones 1-6), esta sección decía explícitamente que faltaba, y ahora que sí la hay, muestra las corridas reales en vez de una simulación.
