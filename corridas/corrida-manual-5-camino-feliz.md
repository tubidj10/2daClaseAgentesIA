# Corrida 5 — Camino feliz (sin datos faltantes)

**Fecha:** 2026-09-03
**Contrato usado:** `prompts/system_prompt.md` (piezas 1, 4, 5, 7) + `prompts/user_prompt.md` (piezas 2, 3, 6).
**Por qué esta corrida:** todas las corridas anteriores (1 a 4) terminan con `datos_faltantes` no vacío — ninguna prueba el camino donde el pedido viene completo y la herramienta confirma todo. Esta lo cubre.

## Input

> "Reinicien el pod notif-worker-1a2b3 en el namespace notificaciones, cluster k8s-cluster-ar1, entorno prod — está reiniciando por un cambio de config que ya aplicamos, sabemos exactamente cuál es."

## Herramienta consultada

```
$ grep -n "Notificaciones" inventario_infraestructura.csv
10:Servicio de Notificaciones,prod,k8s-cluster-ar1,notificaciones,notif-worker-1a2b3
```

Coincidencia única, y además coincide exactamente con lo que el usuario ya declaró (prod, cluster, namespace y pod idénticos a los del inventario).

## Output del agente

```json
{
  "tipo_solicitud": "Incidente",
  "entorno": "prod",
  "titulo_ticket": "Revisión de pod en reinicio - Servicio de Notificaciones",
  "datos_faltantes": []
}
```

## Qué prueba esta corrida

Que el contrato no inventa preguntas cuando no hacen falta: con una sola coincidencia en el inventario y el pedido ya completo, `datos_faltantes` sale `[]` de verdad — no un placeholder, sino el resultado real de que no falta nada por confirmar. Es el contraste directo con las corridas 1, 4 y 5(B) de esta carpeta, donde sí falta algo.
