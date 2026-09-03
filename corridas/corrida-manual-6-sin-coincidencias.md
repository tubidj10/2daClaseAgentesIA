# Corrida 6 — Componente sin coincidencias en el inventario

**Fecha:** 2026-09-03
**Contrato usado:** `prompts/system_prompt.md` (piezas 1, 4, 5, 7) + `prompts/user_prompt.md` (piezas 2, 3, 6).
**Por qué esta corrida:** las corridas 1, 2 y 4 prueban el caso de ambigüedad (el componente existe en más de un entorno). Ninguna prueba el otro extremo: un componente que la herramienta no encuentra en absoluto.

## Input

> "El servicio de recomendaciones está devolviendo 500 en todos los requests desde hace una hora."

## Herramienta consultada

```
$ grep -in "recomendaciones" inventario_infraestructura.csv
(sin resultados)
```

El componente "recomendaciones" no existe en `inventario_infraestructura.csv` — no es que la búsqueda esté mal escrita, es que ese servicio genuinamente no está en el inventario que el agente puede consultar.

## Output del agente

```json
{
  "tipo_solicitud": "Incidente",
  "entorno": "Desconocido",
  "titulo_ticket": "Revisión por errores 500 - Servicio de Recomendaciones",
  "datos_faltantes": [
    "Entorno (dev/qa/prod)",
    "Nombre del clúster de Kubernetes",
    "Namespace y nombre exacto del pod o recurso"
  ]
}
```

## Qué prueba esta corrida

La pieza 7 (Herramienta) es explícita para este caso: *"Si no aparece ninguna fila: seguí las restricciones originales (pedir el dato sin inventar nada)."* El agente no inventa un cluster ni asume que "recomendaciones" es una variante de algún componente que sí conoce (como "Facturación" o "Notificaciones") — directamente admite que no tiene con qué confirmar nada y pide los tres datos en abstracto, igual que en la Entrega 2 antes de tener herramienta. Es la prueba de que la herramienta mejora el output cuando encuentra algo, pero no degrada el comportamiento — ni inventa, ni rompe el contrato — cuando no encuentra nada.
