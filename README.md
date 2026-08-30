# Entrega 2: Instrucción Repetible - Triage de Infraestructura

**Objetivo:** Transformar pedidos informales de desarrolladores en tickets estructurados listos para el backlog.

## 1. Especificación Clara (Las 6 piezas)
Siguiendo la estructura de la clase, el contrato está separado en identidad estable y pedido puntual.
* **System prompt:** Contiene la pieza **1 (Rol)**, la pieza **4 (Restricciones)** y la pieza **5 (Formato)**. Se encuentra en el archivo `system_prompt.md`.
* **User prompt:** Contiene la pieza **2 (Contexto)**, la pieza **3 (Tarea)** y la pieza **6 (Ejemplos)**. Se encuentra en el archivo `user_prompt.md`.

La pieza 5 (Formato) declara explícitamente el esquema de claves (`tipo_solicitud`, `entorno`, `titulo_ticket`, `datos_faltantes`) y los valores permitidos para los dos primeros campos, en lugar de dejar que el modelo infiera el esquema únicamente a partir del ejemplo de la pieza 6. La pieza 6 incluye tres ejemplos que cubren los tres tipos de solicitud más frecuentes (Acceso, Incidente, Despliegue), en línea con la recomendación de la clase de usar dos o tres muestras de entrada→salida.

## 2. Iteraciones Documentadas

### Iteración 1: Control de entornos asumidos
* **Falla:** Al recibir pedidos sin entorno especificado, el modelo asumía que era "Producción", lo cual es un riesgo crítico.
* **Cambio aplicado:** Se modificó la pieza 4 (Restricciones) agregando: *"Prohibido asumir que el entorno es 'Producción' salvo que el usuario lo indique textualmente."*
* **Resultado:** El agente comenzó a clasificar los entornos no mencionados como "Desconocido" y a exigir el dato.

### Iteración 2: Consistencia del esquema JSON
* **Falla:** En pedidos completos, el modelo omitía la clave `datos_faltantes` del JSON, rompiendo la estructura esperada para la lectura automatizada.
* **Cambio aplicado:** Se ajustó la pieza 5 (Formato), agregando: *"El array 'datos_faltantes' debe existir siempre; si no falta nada, devuélvelo como []."*
* **Resultado:** Output 100% predecible y estructurado.

## 2.1 Hallazgo adicional (fuera del alcance de las dos iteraciones pedidas)
Durante las pruebas surgió un tercer problema que documentamos aparte por transparencia, aunque la consigna pide dos iteraciones:

* **Falla:** Al correr el contrato dos veces sin ningún mensaje para procesar, el modelo devolvió dos estructuras JSON completamente distintas entre sí (claves diferentes, valores por defecto diferentes: `null` en una corrida, `"Desconocido"` en la otra), rompiendo la repetibilidad del contrato en el caso borde de entrada vacía.
* **Cambio aplicado:** Se agregó a la pieza 5 (Formato) la definición explícita y cerrada de las cuatro claves obligatorias, sus valores permitidos, y el output exacto a devolver cuando no hay mensaje para procesar.
* **Resultado:** Se corrió nuevamente el caso de mensaje vacío contra el contrato corregido (en otro modelo, Gemini, para además validar portabilidad) y el output coincidió exactamente con el default definido en la pieza 5: `{"tipo_solicitud": "Desconocida", "entorno": "Desconocido", "titulo_ticket": "Esperando mensaje", "datos_faltantes": ["Mensaje original para analizar"]}`. El esquema dejó de variar entre corridas.

## 2.2 Corrección post-entrega (feedback del profesor)

Feedback recibido sobre la Entrega 2: *"Excelente foco en casos borde y estructura exhaustiva. El hallazgo de entrada vacía es especialmente valioso. Agregá una validación JSON..."*

* **Cambio aplicado:** Se agregó a la pieza 5 (Formato) de `system_prompt.md` (y se propagó a `system_prompt_v2.md` de la Entrega 3) una instrucción explícita de auto-validación: antes de responder, el modelo debe verificar que el objeto sea JSON sintácticamente válido (comillas dobles, sin comas colgantes, sin comentarios, llaves/corchetes balanceados) y que tenga exactamente las cuatro claves definidas, corrigiendo cualquier error antes de emitir la respuesta final, sin mostrar ese chequeo en el output.
* **Por qué importa:** las Iteraciones 1 y 2 ya cerraban qué valores y qué claves son válidos, pero ninguna pieza exigía una verificación sintáctica explícita antes de responder; sin ese paso, un error de sintaxis (una coma de más, una comilla simple) podía colarse en el JSON y romper la lectura automatizada, aun cumpliendo el esquema de contenido.

## 3. Output Estructurado en 3 Corridas Reales
Las siguientes tres corridas se ejecutaron contra el contrato ya corregido por las Iteraciones 1 y 2. El detalle de cada una (input y output completo) está en su propio archivo: [`salida_1.md`](./salida_1.md), [`salida_2.md`](./salida_2.md), [`salida_3.md`](./salida_3.md).

**Corrida 1 — Incidente**
* **Input:** "Se cayó la base de datos de QA de nuevo, ¿pueden revisarlo urgente?"
* **Output:** `{"tipo_solicitud": "Incidente", "entorno": "QA", "titulo_ticket": "Revisión por caída de base de datos - QA", "datos_faltantes": ["Nombre exacto de la base de datos", "Ubicación (clúster de Kubernetes, instancia de AWS o servidor)"]}`

**Corrida 2 — Despliegue**
* **Input:** "Necesitamos deployar la versión 1.4 del frontend hoy a las 20hs."
* **Output:** `{"tipo_solicitud": "Despliegue", "entorno": "Desconocido", "titulo_ticket": "Despliegue versión 1.4 - Frontend", "datos_faltantes": ["Entorno (dev/qa/prod)", "Nombre exacto del pipeline, imagen o repositorio", "Ubicación de destino (clúster de Kubernetes, instancia de AWS o servidor)"]}`

**Corrida 3 — Incidente**
* **Input:** "El pod del microservicio de facturación está reiniciándose en loop."
* **Output:** `{"tipo_solicitud": "Incidente", "entorno": "Desconocido", "titulo_ticket": "Revisión de pod en loop de reinicios - Microservicio de facturación", "datos_faltantes": ["Entorno (dev/qa/prod)", "Nombre del clúster de Kubernetes", "Namespace y nombre exacto del pod"]}`

## 4. Reflexión
Escribir este contrato me enseñó que la vaguedad tiene un costo altísimo, pero también que la especificación en sí misma puede quedar incompleta si no se prueba contra casos borde. Separar el *System Prompt* del *User Prompt* fue fundamental para aislar las reglas inquebrantables (Restricciones y Formato) del pedido variable. Sin embargo, el hallazgo más útil surgió al correr el contrato con una entrada vacía: el modelo improvisó dos esquemas JSON distintos entre corridas porque el esquema de salida solo estaba definido implícitamente en el ejemplo de la pieza 6, y ese ejemplo nunca cubría el caso de "sin mensaje". Declarar el esquema de forma explícita y cerrada en la pieza 5, en lugar de depender de que el ejemplo lo insinuara, es lo que terminó de convertir el contrato en algo repetible. Comprendí que exigir un output estructurado no alcanza si la definición de esa estructura no es exhaustiva frente a los casos que el pedido real puede no cubrir.

## 5. Entrega 3: Herramienta

Al contrato de la Entrega 2 le agregué acceso a una herramienta real: `inventario_infraestructura.csv`, una planilla que simula el inventario de componentes desplegados (entorno, clúster, namespace, pod). Se agregó la **pieza 7 (Herramienta)** al system prompt, en `system_prompt_v2.md`, con la regla de consulta: buscar el componente mencionado en el inventario antes de completar `entorno` y `datos_faltantes`, usando el resultado real en vez de adivinar o preguntar en abstracto.

**Corrida documentada** (mismo input que la Corrida 3 de la Entrega 2, para comparar contra la versión sin herramientas): detalle completo de la consulta, el resultado crudo de la herramienta y el output final en [`salida_entrega3_herramienta.md`](./salida_entrega3_herramienta.md).

En resumen, qué cambió: antes, el agente pedía 3 datos genéricos a ciegas (entorno, clúster, namespace/pod) porque no tenía forma de verificar nada. Con la herramienta, el clúster y el namespace dejaron de ser datos faltantes porque el inventario los confirmó; lo único que siguió abierto fue una ambigüedad real (el componente corre tanto en qa como en prod), y el contrato la manejó bien: no asumió "prod" por default, pero en vez de una pregunta abierta le devolvió al desarrollador las dos opciones concretas (con sus pods exactos) para elegir en un solo mensaje. La herramienta no resolvió el 100% del caso porque la ambigüedad era real, pero redujo el ida y vuelta de 3 preguntas genéricas a 1 pregunta puntual con datos reales adjuntos.
