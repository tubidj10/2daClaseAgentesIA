# Entrega 2: Instrucción Repetible - Triage de Infraestructura

**Objetivo:** Transformar pedidos informales de desarrolladores en tickets estructurados listos para el backlog.

## 1. Especificación Clara (Las 6 piezas)
Siguiendo la estructura de la clase, el contrato está separado en identidad estable y pedido puntual.
* **System prompt:** Contiene la pieza **1 (Rol)**, la pieza **4 (Restricciones)** y la pieza **5 (Formato)**. Se encuentra en el archivo `system_prompt.txt`.
* **User prompt:** Contiene la pieza **2 (Contexto)**, la pieza **3 (Tarea)** y la pieza **6 (Ejemplos)**. Se encuentra en el archivo `user_prompt.txt`.

## 2. Iteraciones Documentadas

### Iteración 1: Control de entornos asumidos
* **Falla:** Al recibir pedidos sin entorno especificado, el modelo asumía que era "Producción", lo cual es un riesgo crítico.
* **Cambio aplicado:** Se modificó la pieza 4 (Restricciones) agregando: *"Prohibido asumir que el entorno es 'Producción' salvo que el usuario lo indique textualmente."*
* **Resultado:** El agente comenzó a clasificar los entornos no mencionados como "Desconocido" y a exigir el dato.

### Iteración 2: Consistencia del esquema JSON
* **Falla:** En pedidos completos, el modelo omitía la clave `datos_faltantes` del JSON, rompiendo la estructura esperada para la lectura automatizada.
* **Cambio aplicado:** Se ajustó la pieza 5 (Formato), agregando: *"El array 'datos_faltantes' debe existir siempre; si no falta nada, devuélvelo como []."*
* **Resultado:** Output 100% predecible y estructurado.

## 3. Output Estructurado en 3 Corridas Reales

**Corrida 1**
* **Input:** "Se cayó la base de datos de QA de nuevo, ¿pueden revisarlo urgente?"
* **Output:** `{"tipo_solicitud": "Incidente", "entorno": "QA", "titulo_ticket": "Revisión urgente - Caída de base de datos", "datos_faltantes": []}`

**Corrida 2**
* **Input:** "Necesitamos deployar la versión 1.4 del frontend hoy a las 20hs."
* **Output:** `{"tipo_solicitud": "Despliegue", "entorno": "Desconocido", "titulo_ticket": "Despliegue programado - Frontend v1.4", "datos_faltantes": ["Entorno destino", "Artefacto/Job", "Plan de rollback"]}`

**Corrida 3**
* **Input:** "El pod del microservicio de facturación está reiniciándose en loop."
* **Output:** `{"tipo_solicitud": "Incidente", "entorno": "Desconocido", "titulo_ticket": "CrashLoopBackOff - Pod facturación", "datos_faltantes": ["Entorno", "Namespace"]}`

## 4. Reflexión
Escribir este contrato me enseñó que la vaguedad tiene un costo altísimo. Separar el *System Prompt* del *User Prompt* es fundamental. Al definir las reglas inquebrantables de forma aislada (como forzar el formato JSON y prohibir suposiciones de entornos), el pedido diario se vuelve mucho más seguro. Comprendí que exigir un output estructurado es lo que convierte a un modelo en una pieza real de un sistema automatizado que no requiere copiar y pegar manualmente.
