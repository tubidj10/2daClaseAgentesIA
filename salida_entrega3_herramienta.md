# Entrega 3 — Corrida documentada con herramienta

**Fecha:** 2026-08-28
**Contrato usado:** `system_prompt_v2.md` (piezas 1, 4, 5, 7) + `user_prompt.md` (piezas 2, 3, 6), sin cambios en el user prompt.

## Input (el mismo de la Corrida 3 de la Entrega 2, para comparar manzanas con manzanas)

> "El pod del microservicio de facturación está reiniciándose en loop."

## Qué herramienta tocó y qué le pedí

Herramienta: lectura/búsqueda sobre `inventario_infraestructura.csv`, una planilla real con el inventario de componentes desplegados (columnas `componente`, `entorno`, `cluster`, `namespace`, `pod_o_recurso`).

Consulta ejecutada (grep sobre el componente detectado en el mensaje, "facturación"):

```
$ grep -n "Facturacion" inventario_infraestructura.csv
```

## Qué volvió

```
4:Microservicio de Facturacion,qa,k8s-cluster-ar1,facturacion,facturacion-worker-7c9d1
5:Microservicio de Facturacion,prod,k8s-cluster-ar1,facturacion,facturacion-worker-3a1f4
```

El componente existe en **dos** entornos reales (qa y prod), ambos en el mismo clúster y namespace, con pods distintos. No es una coincidencia única.

## Output final del agente (aplicando la pieza 7 del `system_prompt_v2.md`)

```json
{
  "tipo_solicitud": "Incidente",
  "entorno": "Desconocido",
  "titulo_ticket": "Revisión de pod en loop de reinicios - Microservicio de Facturación",
  "datos_faltantes": [
    "Confirmar entorno afectado: el componente existe en dos instancias reales según inventario — (1) qa, cluster k8s-cluster-ar1, namespace facturacion, pod facturacion-worker-7c9d1; (2) prod, cluster k8s-cluster-ar1, namespace facturacion, pod facturacion-worker-3a1f4. Indicar cuál de las dos está en loop."
  ]
}
```

## Qué cambió contra la versión sin herramientas (Corrida 3, Entrega 2)

Output sin herramienta (README de la Entrega 2):

```json
{"tipo_solicitud": "Incidente", "entorno": "Desconocido", "titulo_ticket": "Revisión de pod en loop de reinicios - Microservicio de facturación", "datos_faltantes": ["Entorno (dev/qa/prod)", "Nombre del clúster de Kubernetes", "Namespace y nombre exacto del pod"]}
```

- **Antes:** 3 datos faltantes genéricos, a ciegas — el agente no sabía nada del componente real y le tiraba la pregunta completa al desarrollador (entorno, clúster, namespace, pod).
- **Después:** el clúster (`k8s-cluster-ar1`) y el namespace (`facturacion`) dejaron de ser datos faltantes porque la herramienta los confirmó — son iguales en ambas instancias reales, así que ya no hace falta preguntarlos.
- Lo único que sigue sin poder resolverse solo es la ambigüedad real entre qa y prod (el componente efectivamente corre en los dos), y el contrato la respeta: no adivina ni asume "prod" por default (pieza 4), pero en vez de una pregunta abierta le devuelve al desarrollador las dos opciones concretas con sus pods exactos para que elija en un solo mensaje.
- Es una mejora honesta, no mágica: la herramienta no resuelve el 100% del caso (porque el dato ambiguo existe de verdad en dos entornos), pero reduce el ida y vuelta de 3 preguntas genéricas a 1 pregunta puntual con los datos reales ya adjuntos.
