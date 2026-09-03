# Corrida 7 — Alta severidad, entorno declarado explícitamente por el usuario

**Fecha:** 2026-09-03
**Contrato usado:** `prompts/system_prompt.md` (piezas 1, 4, 5, 7) + `prompts/user_prompt.md` (piezas 2, 3, 6).
**Por qué esta corrida:** todas las corridas anteriores tienen `entorno: "Desconocido"` en el output. Esta prueba el otro camino legítimo para completar `entorno` sin usar la herramienta: que el usuario lo diga textualmente (pieza 4, restricción sobre "Producción").

## Input

> "URGENTE: en PRODUCCIÓN se cayó completo el checkout, ningún cliente puede pagar, es una emergencia."

## Herramienta consultada

```
$ grep -in "checkout" inventario_infraestructura.csv
(sin resultados)
```

"Checkout" no está en el inventario — no hay componente real para confirmar cluster/namespace/pod. Pero a diferencia de la Corrida 6, acá el usuario **sí** indicó el entorno de forma textual y explícita ("en PRODUCCIÓN"), así que la pieza 4 no aplica como restricción: no es el agente asumiendo "prod" por default, es el dato que el propio mensaje declaró.

## Output del agente

```json
{
  "tipo_solicitud": "Incidente",
  "entorno": "prod",
  "titulo_ticket": "Caída total de checkout - Producción",
  "datos_faltantes": [
    "Nombre del clúster de Kubernetes",
    "Namespace y nombre exacto del pod o servicio de checkout"
  ]
}
```

## Qué prueba esta corrida

Que "no asumas Producción" (Iteración 1) y "usá el entorno si el usuario lo dice" no son reglas en conflicto: la restricción es específicamente contra *inferir* prod cuando no se dijo, no contra aceptarlo cuando sí se dijo. Acá `entorno` sale `"prod"` sin que la herramienta haya confirmado nada — la fuente de verdad para ese campo fue el propio mensaje, tal como permite la pieza 4 desde la Iteración 1. Combinado con la Corrida 6 (misma ausencia en el inventario, pero `entorno: "Desconocido"` porque ahí el usuario no lo dijo), estas dos corridas muestran el contraste completo: la herramienta no es la única fuente legítima de `entorno`, el mensaje del usuario también lo es, y el agente distingue bien entre ambos casos.
