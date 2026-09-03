# Corridas

Dos tipos de corridas conviven en esta carpeta, y es importante no confundirlas:

## Corridas manuales (`corrida-manual-*.md`)

Generadas de forma interactiva: un LLM real aplicando el contrato (`prompts/system_prompt.md` + `prompts/user_prompt.md`) turno a turno en el chat, con llamadas de herramienta reales (`grep` sobre `inventario_infraestructura.csv`) ejecutadas de verdad, no simuladas. Son 7, elegidas para cubrir escenarios distintos, no solo tipos de solicitud distintos:

| # | Escenario | Resultado |
|---|---|---|
| 1 | Incidente, ambigüedad de entorno | Sin herramienta todavía (Entrega 2) — `entorno: Desconocido`, 2 datos faltantes. |
| 2 | Despliegue | Sin herramienta — `entorno: Desconocido`, 3 datos faltantes. |
| 3 | Incidente, mismo caso que la 4 pero sin herramienta | Base de comparación para la Entrega 3. |
| 4 | Incidente + herramienta, ambigüedad real qa/prod | La herramienta reduce 3 preguntas genéricas a 1 pregunta puntual con las 2 opciones reales. |
| 5 | **Camino feliz**: coincidencia única + pedido ya completo | `datos_faltantes: []` — el único caso de esta carpeta donde no falta nada. |
| 6 | **Sin coincidencias** en el inventario | La herramienta no inventa nada cuando no encuentra el componente; se comporta como en la Entrega 2. |
| 7 | **Alta severidad**, entorno declarado explícitamente por el usuario (no por la herramienta) | Prueba que `entorno: "prod"` es válido sin ambigüedad cuando el usuario lo dice textualmente — contraste directo con la corrida 6 (mismo "sin coincidencias", pero `entorno: Desconocido` porque ahí nadie lo dijo). |

## Corridas automatizadas (`corrida_<timestamp>.json`)

Generadas por `./run.sh "mensaje"` (o `python runner.py "mensaje"`), que llama a la API de **Gemini** con tool-calling real, valida el schema de salida con Pydantic, y registra tokens y latencia reales de esa llamada.

Hay **3** corridas reales, generadas con una API key real de Gemini (ver `DECISIONES.md`, Iteraciones 7 y 8):

| Archivo | Input | Resultado |
|---|---|---|
| `corrida_20260903T180353.json` | "El pod del microservicio de facturación está reiniciándose en loop." | Ambigüedad real qa/prod detectada vía la herramienta; el agente no asume, pide elegir entre las dos opciones concretas. |
| `corrida_20260903T180503.json` | "¿Me das permisos para ver los logs del contenedor de pagos?" | Mismo patrón: "App Pagos" también existe en dos entornos (prod y qa) — el agente lo detecta y lo reporta. |
| `corrida_20260903T182003.json` | "Necesitamos deployar la versión 1.4 del frontend hoy a las 20hs." | "Frontend" existe en dev y prod; latencia real de **82.8s** porque el runner esperó de verdad el `retryDelay` de un 429 real (ver más abajo) antes de reintentar con éxito. |

**Por qué no hay una cuarta (mensaje vacío):** al generar estas corridas, el runner recibió varios `429 RESOURCE_EXHAUSTED` reales de Gemini — la cuota gratuita del free tier para este modelo se agotó en el proceso de probar el runner (varias llamadas de diagnóstico + las correcciones de código documentadas en `DECISIONES.md` + estas 3 corridas). En el intento de la corrida de mensaje vacío, el runner esperó el `retryDelay` real del servidor en cada uno de los 5 reintentos (~5 minutos en total) y aun así la cuota seguía agotada — **no se fabricó un resultado falso para completar la tabla**. Esa categoría sí está cubierta por corridas manuales reales, incluyendo el caso de entrada vacía documentado en `DECISIONES.md` (Iteración 2.1).

Tokens y latencia reales de cada corrida están dentro de cada JSON (`tokens_input`, `tokens_output`, `latencia_segundos`) — esa es la métrica diferencial que pedía `DECISIONES.md`. Nota: `tokens_output` incluye los "thinking tokens" de Gemini, que se facturan como output aunque la API los reporta en un campo separado (ver `COSTOS.md`).

Para generar una corrida nueva (una vez que la cuota se reinicie):

```bash
cp .env.example .env   # completar GEMINI_API_KEY
./run.sh "tu mensaje acá"
```
