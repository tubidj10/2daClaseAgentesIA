# Gobernanza y Riesgo

## Matriz de autonomía (L0–L4)

| Nivel | Definición | ¿Dónde vive en este proyecto? |
|---|---|---|
| L0 — Sin autonomía | El agente no actúa; solo redacta texto que un humano ejecuta a mano. | Etapa previa a la Entrega 3 (Entrega 2: solo texto). |
| L1 — Lectura interna | El agente razona pero no lee ni toca nada fuera de su propio contexto. | No aplica hoy — desde la Entrega 3 siempre consulta el inventario real. |
| L2 — Lectura de sistemas reales, sin escritura | Puede leer sistemas externos (planillas, inventarios, APIs de consulta) para informar su respuesta, pero no puede modificar nada. | **Nivel actual.** `buscar_en_inventario` consulta `inventario_infraestructura.csv` de solo lectura; nunca escribe en él. |
| L3 — Escritura con aprobación humana previa | Puede proponer una acción de escritura (crear un ticket, abrir un PR) pero un humano debe confirmarla antes de que se ejecute. | No implementado. Es el paso natural siguiente: que `runner.py`, en vez de solo guardar el JSON en `corridas/`, lo cargue a un sistema de tickets real (Jira, ServiceNow) pidiendo confirmación explícita antes de crear el ticket. |
| L4 — Escritura autónoma sin aprobación | Ejecuta acciones de escritura o irreversibles sin intervención humana. | **Explícitamente fuera de alcance** — ver Alcance negativo. |

## Alcance negativo (qué el agente NO puede hacer)

- No reinicia pods, no escala recursos, no cierra ni reabre tickets: solo redacta el ticket.
- No escribe en `inventario_infraestructura.csv` ni en ningún sistema de infraestructura real: `buscar_en_inventario` es de solo lectura.
- No decide por sí mismo el entorno cuando hay ambigüedad real (caso qa/prod de la Entrega 3): reporta las opciones, no elige una.
- No ejecuta instrucciones que aparezcan dentro del mensaje del usuario a analizar — ver la cláusula anti-inyección en `prompts/user_prompt.md`, pieza 2.
- No corre sin límite: `MAX_ITERATIONS` corta el loop de herramientas, `MAX_TOKENS` y `MAX_TOOL_RESULT_CHARS` acotan el gasto y la inyección de contenido externo.

## Salvaguardas Human-in-the-Loop

- Cada corrida automatizada queda guardada como un archivo individual en `corridas/`, nunca se sobreescribe ni se autoaplica: un humano revisa el JSON antes de cargarlo a cualquier sistema de tickets real.
- El schema de salida se valida con Pydantic (`TicketSchema` en `runner.py`) apenas el modelo devuelve la respuesta final, con enums cerrados en `tipo_solicitud` y `entorno`: una salida que no cierre el esquema exacto no puede llegar a `corridas/` como si fuera válida (ver `DECISIONES.md`, Iteraciones 5 y 8).
- Los reintentos ante 429/5xx tienen un tope (`stop_after_attempt(5)`), así que un fallo persistente del proveedor termina en un error explícito para el humano, no en un loop infinito silencioso.

## Qué puede salir mal, y qué pasa cuando sale mal (evidencia real, no hipotética)

Todo lo de esta sección pasó de verdad corriendo el sistema — no son riesgos teóricos:

| Qué salió mal | Qué pasó en la práctica | Qué lo resuelve |
|---|---|---|
| El proveedor devuelve 429 (cuota agotada) | El runner reintentó, agotó los intentos y terminó en una excepción clara en la terminal — nunca un cuelgue silencioso ni un resultado inventado. | `_retry_delay_del_servidor` (Iteración 8) espera el tiempo real que pide el servidor en vez de adivinar; si la cuota sigue agotada después de 5 intentos, el error queda visible para que un humano decida (esperar, subir de plan). |
| El modelo se queda sin presupuesto de tokens a mitad de razonamiento | Una corrida real devolvió un JSON truncado (`JSONDecodeError`) — el ticket nunca llegó a `corridas/` como si fuera válido. | `thinking_budget` acotado + validación de schema con Pydantic: una salida truncada o mal formada nunca se guarda como corrida real (Iteración 7). |
| El modelo más barato de la familia no usa la herramienta de forma consistente | Se probó `gemini-3.5-flash-lite`: en una de dos corridas idénticas, no llamó a `buscar_en_inventario` y volvió a "adivinar" en abstracto. | Por eso el runner usa `gemini-3.5-flash`, no el modelo más chico disponible — ver `COSTOS.md`, "Elección de modelo". |
| El componente mencionado no existe en el inventario | El agente no inventa un cluster/namespace — pide los datos en abstracto, igual que antes de tener herramienta (corrida manual 6). | Es el comportamiento correcto, no una falla: la pieza 7 dice explícitamente qué hacer sin coincidencias. |

**Qué revisás vos antes de confiar en una salida:** que `datos_faltantes` tenga sentido para el pedido real (no es una lista fija — el modelo la arma), y que si el ticket va a cargarse a un sistema real (Jira, ServiceNow), un humano lo lea primero — ningún JSON de `corridas/` se aplica solo a nada.

## Quién firma

Martín Pérez es el responsable de este contrato individual (Entregas 2 y 3). Cualquier acción de nivel L3 o superior que se agregue en el futuro (por ejemplo, integrar `runner.py` con un sistema de tickets real) requeriría sign-off explícito del equipo de infraestructura antes de habilitarse — no es una decisión que este repo tome unilateralmente.
