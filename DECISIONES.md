# Decisiones e Iteraciones

Historial de las fallas reales encontradas al probar el contrato, el cambio aplicado en cada caso, y el commit exacto donde quedó. Cuando existe una métrica diferencial real (tokens/latencia), se reporta; cuando no, se dice explícitamente que está pendiente en vez de inventarla — ver la nota al final.

## Iteración 1 — Control de entornos asumidos

- **Falla:** al recibir pedidos sin entorno especificado, el modelo asumía que era "Producción", lo cual es un riesgo crítico.
- **Cambio aplicado:** se agregó a la pieza 4 (Restricciones): *"Prohibido asumir que el entorno es 'Producción' salvo que el usuario lo indique textualmente."*
- **Resultado:** el agente empezó a clasificar los entornos no mencionados como "Desconocido" y a exigir el dato.
- **Commit:** incluida en `832a728` (versión base de la Entrega 2, ya con las iteraciones 1 y 2 aplicadas).

## Iteración 2 — Consistencia del esquema JSON

- **Falla:** en pedidos completos, el modelo omitía la clave `datos_faltantes` del JSON, rompiendo la estructura esperada para lectura automatizada.
- **Cambio aplicado:** se ajustó la pieza 5 (Formato): *"El array 'datos_faltantes' debe existir siempre; si no falta nada, devuélvelo como []."*
- **Resultado:** output 100% predecible y estructurado.
- **Commit:** `832a728`.

## Iteración 2.1 — Hallazgo de entrada vacía

- **Falla:** al correr el contrato dos veces sin ningún mensaje para procesar, el modelo devolvió dos estructuras JSON completamente distintas entre sí (claves diferentes, valores por defecto diferentes), rompiendo la repetibilidad en el caso borde de entrada vacía.
- **Cambio aplicado:** se agregó a la pieza 5 la definición explícita y cerrada de las cuatro claves obligatorias, sus valores permitidos, y el output exacto a devolver cuando no hay mensaje para procesar.
- **Resultado:** se corrió nuevamente el caso de mensaje vacío contra el contrato corregido (en otro modelo, Gemini, para validar portabilidad) y el output coincidió exactamente con el default definido en la pieza 5.
- **Commit:** `832a728`.

## Iteración 3 — Herramienta real (Entrega 3)

- **Motivación:** el contrato solo procesaba texto que un humano le pegaba; no tenía forma de verificar nada contra la realidad.
- **Cambio aplicado:** se agregó la pieza 7 (Herramienta): consultar `inventario_infraestructura.csv` (inventario real de componentes) antes de completar `entorno` y `datos_faltantes`.
- **Resultado:** corrida real documentada en `corridas/corrida-manual-4-entrega3-herramienta.md`. El caso de prueba (componente "Facturación") reveló una ambigüedad real — existe en `qa` y en `prod` — y el contrato la manejó bien: no asumió un entorno, pero reemplazó 3 preguntas genéricas por 1 pregunta puntual con las dos opciones reales.
- **Commit:** `0040ee4`.

## Iteración 4 — Validación JSON (corrección post-entrega del profesor)

- **Feedback recibido:** *"Excelente foco en casos borde y estructura exhaustiva. El hallazgo de entrada vacía es especialmente valioso. Agregá una validación JSON..."*
- **Cambio aplicado:** se agregó a la pieza 5 una instrucción explícita de auto-validación sintáctica antes de responder (comillas dobles, sin comas colgantes, llaves balanceadas, exactamente las cuatro claves).
- **Commit:** `5d247c9`.

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
- **Commit:** este mismo commit (ver `git log -- runner.py GOBERNANZA.md COSTOS.md` para el hash exacto).

## Nota sobre métricas diferenciales (tokens/latencia)

`runner.py` registra `tokens_input`, `tokens_output` y `latencia_segundos` reales por corrida, pero **no había una `ANTHROPIC_API_KEY` disponible al momento de esta entrega** para generar corridas automatizadas reales (ver `corridas/README.md`). No se fabricó un número de latencia o de tokens para esta tabla: eso sería exactamente el tipo de dato simulado que el propio informe de auditoría penaliza ("Anti-Mocking/Slop"). Cuando se corra `runner.py` con una key real, cada `corridas/corrida_<timestamp>.json` va a traer esa métrica, y esta sección se actualiza con el antes/después real.
