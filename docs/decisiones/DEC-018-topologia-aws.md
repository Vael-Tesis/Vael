# DEC-018 — Topología mínima en AWS sin NAT Gateway

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-16 |
| Tarea de origen | PLN-C-02 (decisión 9, adelantada por DEC-017) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Modifica | DEC-016, punto 6: las Lambdas ya no abren sesión en la base de datos |
| Relacionada con | DEC-010 (aislamiento), DEC-011 (autenticación), DEC-016 (SQS + Lambda) |

## Contexto

- La API en ECS necesita llegar a RDS, a la API de Gemini (internet), a Secrets Manager, ECR, CloudWatch y SQS.
- Las Lambdas de DEC-016 necesitan llegar a Gemini y persistir su resultado.
- RDS no debe ser accesible desde internet.
- Una Lambda dentro de una VPC no obtiene IP pública: para salir a internet requiere un NAT Gateway, que tiene un costo fijo por hora y por datos procesados.
- No hay un dominio propio confirmado: `EMAIL_FROM=noreply@vael.ai` en `.env.example` asume uno, pero no existe registro de su adquisición.
- DEC-017 exige desplegar un esqueleto en AWS al cierre del Sprint 1 (23 de octubre).

## Decisión

### Red

| Elemento | Configuración |
|---|---|
| VPC | 2 zonas de disponibilidad (requisito del ALB y del grupo de subredes de RDS) |
| Subredes públicas | ALB y tareas de ECS (con IP pública solo para salida) |
| Subredes privadas | RDS, sin ruta a internet |
| NAT Gateway | **Ninguno** |

### Grupos de seguridad

| Grupo | Entrada permitida |
|---|---|
| ALB | 80/443 solo desde el rango de orígenes de CloudFront (prefix list administrada por AWS) |
| ECS | 8000 solo desde el grupo del ALB |
| RDS | 5432 solo desde el grupo de ECS |

### Cómputo y datos

| Componente | Configuración |
|---|---|
| ECS Fargate | 1 tarea (0.5 vCPU, 1 GB), escalado por CPU hasta 2; Gunicorn con 2 workers |
| RDS PostgreSQL 16 | Instancia de la familia t (la más pequeña que soporte la carga de pruebas), **una sola zona**, backups automáticos con retención de 7 días, roles de DEC-010 |
| Lambda | **Fuera de la VPC**. Consume SQS, descarga el CV de S3, llama a Gemini y **entrega el resultado al backend** por un endpoint interno |
| SQS | Colas de DEC-016 con su DLQ |

### Entrada única con CloudFront

CloudFront es el único punto de entrada:
- `/*` → S3 (build del frontend).
- `/api/*` → ALB.

Esto da HTTPS con el certificado de `*.cloudfront.net` sin necesidad de un dominio propio, evita CORS (un solo origen para el navegador) y permite que el ALB solo acepte tráfico de CloudFront.

### Endpoint interno para las Lambdas

- Ruta bajo `/api/interno/...`, excluida del OpenAPI público.
- Autenticación con **firma HMAC-SHA256** del cuerpo y de una marca de tiempo, usando un secreto en Secrets Manager (reemplaza el uso directo de `INTERNAL_SERVICE_KEY`).
- Rechaza peticiones con más de 5 minutos de antigüedad (protección contra reenvíos).
- El mensaje incluye el `tenant_id`; el backend lo fija y persiste con la RLS (DEC-010). La idempotencia se verifica en el backend.

### Dominio propio

**Dominio decidido: `vael.work`**, a adquirir en GoDaddy (decisión del equipo, 2026-10-18). Su compra y configuración entran como una historia del backlog; la topología no depende de él.

- Se agrega como nombre alternativo de CloudFront, con un certificado de ACM emitido en `us-east-1`.
- Se verifica en SES con registros DKIM, SPF y DMARC; el remitente pasa a ser `noreply@vael.work`.
- **Pendiente:** dónde se administra el DNS. Con el DNS en GoDaddy solo puede apuntarse un subdominio (por ejemplo, `app.vael.work`) a CloudFront; delegándolo a Route 53 también puede usarse la raíz `vael.work`.
- **SUPUESTO por verificar:** la reputación del dominio `.work` en los filtros de spam; se prueba el envío a Gmail y Outlook tras configurar SPF, DKIM y DMARC.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| A. Red privada completa con un NAT Gateway por zona | Costo fijo de red alto para un sistema en etapa de tesis |
| B. ECS en subred pública y Lambda en la VPC con un NAT Gateway | Mantiene un costo fijo de NAT solo para que la Lambda acceda a RDS |
| Lambda fuera de la VPC con RDS accesible públicamente | Expone la base de datos a internet; las IP de Lambda no son fijas, así que no se pueden restringir |
| RDS Multi-AZ | Duplica el costo de la base de datos; la alta disponibilidad no es un requisito de la tesis |

## Trade-off aceptado

- Las tareas de ECS tienen IP pública. Se mitiga con un grupo de seguridad que solo admite tráfico entrante desde el ALB.
- El endpoint interno es alcanzable a través del ALB. Se mitiga con la firma HMAC y la ventana de tiempo.
- RDS en una sola zona: una falla de la zona deja el sistema sin base de datos hasta restaurarla. Aceptable para la tesis; en producción real se recomienda Multi-AZ.
- Los costos son **SUPUESTOS** hasta verificarlos con la calculadora oficial de AWS (DEP-C-01).

## Consecuencias

| Elemento | Cambio |
|---|---|
| DEC-016 | Punto 6 modificado: la Lambda entrega el resultado al backend; no abre sesión en la base de datos |
| DEV-C-13 | Incluye el endpoint interno con firma HMAC y su test |
| DEP-C-02 | Aprovisiona esta topología |
| DEP-C-03 | Rol de la Lambda: SQS, lectura de S3 y lectura del secreto HMAC; sin acceso a RDS |
| Doc 03 y doc 09 | Diagrama y aprovisionamiento con esta topología |
| Monografía, apartado 3.1.1 | Diagrama de arquitectura con esta topología |

## Validación

- RDS no responde desde internet.
- El ALB rechaza peticiones que no vienen de CloudFront.
- El endpoint interno rechaza peticiones sin firma, con firma inválida o con una marca de tiempo vencida.
- Un CV cargado en producción genera su recomendación pasando por SQS, Lambda y el endpoint interno.
- La aplicación funciona por HTTPS en el dominio de CloudFront.
