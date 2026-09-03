# Triage de Infraestructura — Contrato + Herramienta

Agente de triage: convierte pedidos informales de desarrolladores en tickets estructurados (JSON), consultando un inventario real de infraestructura antes de adivinar nada. Trabajo individual — Martín Pérez — para la materia Programación de y con Agentes de IA (MADE/MBA UCEMA).

## Estructura del repo

| Ruta | Qué es |
|---|---|
| `prompts/system_prompt.md` | Rol, restricciones, formato (schema + auto-validación) y la herramienta — piezas 1, 4, 5, 7 del contrato. |
| `prompts/user_prompt.md` | Contexto, tarea y ejemplos few-shot — piezas 2, 3, 6. Incluye la cláusula anti-inyección sobre el mensaje del usuario. |
| `inventario_infraestructura.csv` | La herramienta: inventario real de componentes (`componente, entorno, cluster, namespace, pod_o_recurso`) que el agente consulta antes de completar `entorno`/`datos_faltantes`. |
| `runner.py` | Runner en Python: llama a la API de Anthropic con tool-calling real, fuerza el schema de salida a nivel de protocolo, reintenta ante 429/5xx con backoff+jitter, y guarda cada corrida en `corridas/`. |
| `tests/test_runner.py` | Tests con `pytest` de la lógica que no depende de la API (búsqueda en inventario, validación de schema). |
| `corridas/` | Corridas reales — manuales (chat) y automatizadas (`runner.py`). Ver `corridas/README.md`. |
| `DECISIONES.md` | Historial de fallas encontradas, cambios aplicados y el commit exacto de cada iteración. |
| `GOBERNANZA.md` | Matriz de autonomía L0–L4, alcance negativo y salvaguardas human-in-the-loop. |
| `COSTOS.md` | Análisis económico con precios reales de Claude Sonnet 5, sensibilidad de Prompt Caching y el impacto de picos de carga sobre el SLO. |

## Cómo correr una corrida real

```bash
pip install -r requirements.txt
cp .env.example .env   # completar ANTHROPIC_API_KEY
python runner.py "El pod del microservicio de facturación está reiniciándose en loop."
```

El resultado se imprime en pantalla y queda guardado en `corridas/corrida_<timestamp>.json` con tokens y latencia reales.

Para correr los tests (no requieren API key):

```bash
pytest
```

## El contrato, en una línea

Un system prompt fijo (rol + restricciones + formato) separado de un user prompt variable (contexto + tarea + ejemplos), con una herramienta de solo lectura en el medio: el agente nunca inventa un entorno, cluster o pod — si el inventario no lo confirma, lo marca como faltante. El detalle de por qué cada pieza quedó así, y qué se rompió antes de llegar a esta versión, está en `DECISIONES.md`.
