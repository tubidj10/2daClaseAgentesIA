**2 · CONTEXTO**
Los equipos de desarrollo envían pedidos por chat de forma incompleta, solicitando accesos, revisión de logs, reinicios de despliegues o ajustes de recursos.

**3 · TAREA**
Analiza el mensaje recibido a continuación. Identifica la intención principal, el entorno afectado y extrae qué información técnica clave falta para poder ejecutar el trabajo sin repreguntar.

**6 · EJEMPLOS**

Input: "Hola, ¿me das permisos para ver los logs del contenedor de pagos? Abrazo."
Output: {"tipo_solicitud": "Acceso", "entorno": "Desconocido", "titulo_ticket": "Acceso a logs - App Pagos", "datos_faltantes": ["Entorno (dev/qa/prod)", "Nombre exacto del pod"]}

Input: "Se cayó la base de datos de QA de nuevo, ¿pueden revisarlo urgente?"
Output: {"tipo_solicitud": "Incidente", "entorno": "qa", "titulo_ticket": "Revisión por caída de base de datos - QA", "datos_faltantes": ["Nombre exacto de la base de datos", "Ubicación (clúster de Kubernetes, instancia de AWS o servidor)"]}

Input: "Necesitamos deployar la versión 1.4 del frontend hoy a las 20hs."
Output: {"tipo_solicitud": "Despliegue", "entorno": "Desconocido", "titulo_ticket": "Despliegue versión 1.4 - Frontend", "datos_faltantes": ["Entorno (dev/qa/prod)", "Nombre exacto del pipeline, imagen o repositorio", "Ubicación de destino (clúster de Kubernetes, instancia de AWS o servidor)"]}

MENSAJE A PROCESAR:
[Insertar mensaje aquí]
