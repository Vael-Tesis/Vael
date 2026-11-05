# Infraestructura de VAEL en AWS (DEP-C-01)

Topología de DEC-018. El entorno **se enciende solo para usarlo** (demos, E3, sustentación) y se apaga después (decisión de operación del 2026-10-25, doc 09).

| Pila | Contenido | Vida | Costo con el backend apagado |
|---|---|---|---|
| `vael-base` (`base.yaml`) | ECR, buckets del panel y de la landing, CloudFront para `app.vael.work` y `www.vael.work` | Permanente | ~0 USD (almacenamiento de pocos MB) |
| `vael-entorno` (`entorno.yaml`) | VPC sin NAT, ALB, ECS Fargate, RDS PostgreSQL 16, bucket de los CV, secretos y logs | Temporal | — |

Fuera de las pilas: el certificado de ACM (`vael.work`, `www.vael.work`, `app.vael.work`, validado por DNS en GoDaddy) y el parámetro `/vael/origen-secreto` de SSM (cabecera que CloudFront envía al ALB).

## Encender y apagar

Requisitos: AWS CLI con el perfil `vael`, Docker Desktop encendido, `backend/.env` con `GEMINI_API_KEY` y `SEED_PASSWORD`.

```powershell
.\scripts\aws-encender.ps1   # ~20 min la primera vez; ~5 min si el entorno ya existe
.\scripts\aws-apagar.ps1     # ~10 min; destruye RDS y los CV de prueba
```

El encendido crea la base de datos desde cero cada vez: roles (DEC-010), migraciones y datos semilla (doc 13). Los usuarios semilla usan la misma `SEED_PASSWORD` del entorno local.

## Costo aproximado del entorno encendido (us-east-1, precios de lista)

| Recurso | Por hora (USD) |
|---|---|
| ALB | ~0,030 |
| ECS Fargate (0,5 vCPU, 1 GB) | ~0,025 |
| RDS db.t4g.micro + 20 GB | ~0,019 |
| IPs públicas (3) | ~0,015 |
| CloudFront, S3, logs, secretos | ~0 |
| **Total** | **~0,09** (3 horas ≈ 0,30; un día olvidado ≈ 2,20) |

Se descuenta de los créditos del plan Free. El presupuesto `vael-mensual` avisa al pasar los 20 USD.

## DNS en GoDaddy (una sola vez)

| Tipo | Nombre | Valor |
|---|---|---|
| CNAME | `app` | Dominio de la distribución de la app (lo imprime el encendido) |
| CNAME | `www` | Dominio de la distribución de la landing (lo imprime el encendido) |
| Reenvío | `vael.work` | `https://www.vael.work` (permanente, 301) |

Más los tres CNAME `_xxxx` de validación del certificado, que no se borran.

## Seguridad

- El ALB solo acepta tráfico de CloudFront (lista de prefijos administrada) y solo reenvía si llega la cabecera `X-Origen-Vael`.
- El backend solo recibe tráfico del ALB; RDS, solo del backend, y está en subredes sin salida a internet.
- Los buckets son privados: CloudFront lee los sitios con OAC y el backend lee y escribe los CV con el rol de la tarea.
- `DEBUG=false` en producción (sin `/docs`). La URL del administrador de la base y la contraseña de las semillas solo llegan a la tarea de preparación, no al servicio.

## Pendiente

- SES (HU-24): sin el dominio verificado, los correos no se envían en AWS. El error queda en el log y las decisiones se registran igual.
- SQS + Lambda (HU-23, DEC-016): el despachador sigue en modo en proceso.
