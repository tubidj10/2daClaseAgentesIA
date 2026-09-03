# Corridas

Dos tipos de corridas conviven en esta carpeta, y es importante no confundirlas:

## Corridas manuales (`corrida-manual-*.md`)

Generadas de forma interactiva: un LLM real aplicando el contrato (`prompts/system_prompt.md` + `prompts/user_prompt.md`) turno a turno en el chat, incluyendo — en la corrida 4 — una llamada de herramienta real (`grep` sobre `inventario_infraestructura.csv`) ejecutada de verdad, no simulada. Cubren las 4 categorías del contrato (Incidente ×2, Despliegue, Acceso vía la herramienta).

## Corridas automatizadas (`corrida_<timestamp>.json`)

Generadas por `./run.sh "mensaje"` (o `python runner.py "mensaje"`), que llama a la API de **Gemini** con tool-calling real, valida el schema de salida con Pydantic, y registra tokens y latencia reales de esa llamada.

Hay **2** corridas reales, generadas con una API key real de Gemini (ver `DECISIONES.md`, Iteración 7):

| Archivo | Input | Resultado |
|---|---|---|
| `corrida_20260903T180353.json` | "El pod del microservicio de facturación está reiniciándose en loop." | Ambigüedad real qa/prod detectada vía la herramienta; el agente no asume, pide elegir entre las dos opciones concretas. |
| `corrida_20260903T180503.json` | "¿Me das permisos para ver los logs del contenedor de pagos?" | Mismo patrón: "App Pagos" también existe en dos entornos (prod y qa) — el agente lo detecta y lo reporta. |

**Por qué no hay más:** al generar estas corridas, el runner recibió un `429 RESOURCE_EXHAUSTED` real de Gemini — la cuota gratuita del free tier es de **20 requests/día** para este modelo, y se agotó en el proceso de probar el runner (varias llamadas de diagnóstico + las correcciones de código documentadas en `DECISIONES.md` + estas 2 corridas). Las corridas de "Despliegue" y de mensaje vacío quedaron sin generar por API hasta que la cuota se reinicie o se agregue un plan pago — **no se fabricó un resultado falso para completar la tabla**. Esas dos categorías sí están cubiertas por corridas manuales reales (ver arriba).

Tokens y latencia reales de cada corrida están dentro de cada JSON (`tokens_input`, `tokens_output`, `latencia_segundos`) — esa es la métrica diferencial que pedía `DECISIONES.md`. Nota: `tokens_output` incluye los "thinking tokens" de Gemini, que se facturan como output aunque la API los reporta en un campo separado (ver `COSTOS.md`).

Para generar una corrida nueva (una vez que la cuota se reinicie):

```bash
cp .env.example .env   # completar GEMINI_API_KEY
./run.sh "tu mensaje acá"
```
