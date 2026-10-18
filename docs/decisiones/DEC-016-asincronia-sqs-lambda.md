# DEC-016 — Procesamiento asíncrono con Amazon SQS + AWS Lambda

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-14 |
| Tarea de origen | PLN-C-02 (decisión de topología, parte asíncrona); corrección ENT-06 |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Coherente con | Monografía E2 v1.1, Tabla 2.7 (Cómputo): "Lambda se reserva para tareas asíncronas breves" |
| Relacionada con | DEC-010 (aislamiento), DEC-013 (idempotencia del correo de cierre) |

## Contexto

- **HECHO (código, 2026-10-13):** las tareas asíncronas (análisis de CV, análisis de la entrevista y correos) se ejecutan como `BackgroundTasks` de FastAPI dentro del contenedor de ECS. `encolar_tarea` (SQS) existe, pero no se usa.
- **HECHO (monografía entregada):** la Tabla 2.7 y la sección 2.4 reservan AWS Lambda para las tareas asíncronas breves.
- Con `BackgroundTasks`, una tarea en curso se pierde si el contenedor se reinicia o se reemplaza durante un despliegue, no hay reintentos y compite por CPU con las peticiones de la API.

## Decisión

1. **Producción:** las tareas asíncronas se publican en colas de **Amazon SQS** y las procesan funciones **AWS Lambda**.
2. **Colas iniciales:** `vael-analisis-cv` y `vael-analisis-entrevista`. El envío de correos se evalúa en DEV: puede quedar síncrono si su latencia es baja. Las capturas de auditoría se agregan en el ciclo 2.
3. **Cola de mensajes fallidos (DLQ)** por cada cola, con alarma de CloudWatch si recibe algún mensaje.
4. **Mismo código:** las Lambdas se empaquetan como **imagen de contenedor** construida desde el backend y publicada en ECR, para reutilizar los servicios sin duplicarlos.
5. **Despachador único:** el código no llama a SQS ni a `BackgroundTasks` directamente, sino a una función `despachar_tarea(tipo, payload)`. En producción publica en SQS; en desarrollo y en los tests ejecuta la tarea en el mismo proceso.
6. **Aislamiento (DEC-010):** cada mensaje incluye el `tenant_id`; la Lambda abre su sesión como `vael_app` y lo fija antes de cualquier consulta.
7. **Idempotencia:** SQS entrega cada mensaje al menos una vez, así que cada tarea verifica el estado del candidato antes de actuar y no duplica filas, tokens ni correos.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Mantener `BackgroundTasks` en ECS | Pierde tareas ante reinicios y despliegues, no reintenta y contradice la Tabla 2.7 entregada |
| Servicio worker en ECS que consume SQS | Técnicamente viable, pero mantiene un contenedor encendido para una carga irregular y también contradice la Tabla 2.7 |

## Trade-off aceptado y consecuencia de red

- Más piezas que operar: colas, DLQ, funciones, permisos y empaquetado.
- **Consecuencia que debe resolver la decisión de topología:** la Lambda necesita llegar a RDS (subred privada) **y** a internet (API de Gemini). Una Lambda dentro de una VPC no obtiene IP pública, así que el acceso a internet requiere un **NAT Gateway** (o una alternativa equivalente). El NAT tiene un costo por hora y por datos procesados que **debe verificarse en la calculadora oficial de AWS** antes de aprovisionar. Lo mismo aplica a las tareas de ECS si se ubican en subredes privadas.

## Consecuencias

Cambios en el roadmap:

| Tarea | Cambio |
|---|---|
| DEV-C-13 (nueva) | Despachador `despachar_tarea`, handlers de Lambda para el análisis de CV y de la entrevista, imagen de contenedor para Lambda, modo en proceso para desarrollo y tests |
| DEP-C-02 | Agrega SQS, DLQ, Lambda y la red necesaria (NAT o alternativa) según la decisión de topología |
| DEP-C-03 | Permisos de la tarea ECS para publicar en SQS; rol propio de cada Lambda con permisos mínimos |
| DEP-C-05 | El pipeline también publica la imagen de Lambda y actualiza las funciones |
| DEP-C-06 | Alarma de DLQ con mensajes |

Documentos a actualizar: docs 03, 04, 08 y 09 (procesamiento asíncrono); monografía, corrección ENT-06 resuelta a favor de lo entregado.

## Validación

- Test: en desarrollo, `despachar_tarea` ejecuta la tarea en el proceso y el candidato queda en `cv_por_confirmar`.
- Test: procesar dos veces el mismo mensaje no duplica la recomendación ni los correos.
- Test: un mensaje sin `tenant_id` se rechaza y no accede a datos.
- Prueba en AWS: un CV cargado en producción genera su recomendación a través de SQS y Lambda; un mensaje forzado a fallar termina en la DLQ y dispara la alarma.
