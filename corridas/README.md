# Corridas

Dos tipos de corridas conviven en esta carpeta, y es importante no confundirlas:

## Corridas manuales (`corrida-manual-*.md`)

Generadas de forma interactiva: un LLM real aplicando el contrato (`prompts/system_prompt.md` + `prompts/user_prompt.md`) turno a turno en el chat, incluyendo — en la corrida 4 — una llamada de herramienta real (`grep` sobre `inventario_infraestructura.csv`) ejecutada de verdad, no simulada. Son la evidencia de las Entregas 2 y 3 antes de que existiera `runner.py`.

## Corridas automatizadas (`corrida_<timestamp>.json`)

Generadas por `python runner.py "mensaje"`, que llama a la API de Anthropic con tool-calling real, fuerza el schema de salida a nivel de protocolo, y registra tokens y latencia reales de esa llamada. **Esta carpeta no tiene ninguna todavía**: requieren una `ANTHROPIC_API_KEY` real (ver `.env.example`), y al momento de esta entrega no había una disponible. El código está completo y probado (`tests/test_runner.py` cubre la lógica que no depende de la API); lo que falta es correrlo con credenciales reales — deliberadamente no se fabricó un output de API falso para llenar este hueco (ver `DECISIONES.md`).

Para generar la primera corrida automatizada real:

```bash
pip install -r requirements.txt
cp .env.example .env   # completar ANTHROPIC_API_KEY
python runner.py "El pod del microservicio de facturación está reiniciándose en loop."
```

El resultado queda en `corridas/corrida_<timestamp>.json`, con `tokens_input`, `tokens_output` y `latencia_segundos` reales — la métrica diferencial que pide `DECISIONES.md`.
