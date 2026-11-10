# Infraestructura de VAEL en AWS (DEP-C-01)

Topología de DEC-018. El entorno **se enciende solo para usarlo** (demos, E3, sustentación) y se apaga después (decisión de operación del 2026-10-25, doc 09).

| Pila | Contenido | Vida | Costo con el backend apagado |
|---|---|---|---|
| `vael-base` (`base.yaml`) | ECR, buckets del panel y de la landing, CloudFront para `app.vael.work` y `www.vael.work` | Permanente | ~0 USD (almacenamiento de pocos MB) |
| `vael-entorno` (`entorno.yaml`) | VPC sin NAT, ALB, ECS Fargate, RDS PostgreSQL 16, bucket de los CV, SQS y Lambda (HU-23), alarmas (HU-22), secretos y logs | Temporal | — |
| `vael-acceso` (`acceso.yaml`) | Federación OIDC con GitHub, rol `vael-github-despliegue` (solo este repositorio desde `main`) y rol de servicio `vael-cloudformation` (DEP-C-05) | Permanente; se despliega a mano y el flujo no puede modificarla | 0 USD |

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

## Despliegue automático (DEP-C-05)

`.github/workflows/deploy.yml` usa los mismos scripts desde GitHub Actions, sin claves guardadas:

- **Al integrar en `main`:** publica las imágenes en ECR y la landing. Si el entorno está encendido, también lo actualiza con el código nuevo. Si está apagado, no enciende nada.
- **Manual** (Actions → Despliegue → Run workflow, desde `main`): `encender` o `apagar`.

Configuración (una sola vez):

```powershell
aws cloudformation deploy --stack-name vael-acceso --template-file infra/aws/acceso.yaml `
  --capabilities CAPABILITY_NAMED_IAM --tags Proyecto=VAEL --profile vael --region us-east-1
```

En GitHub (Settings → Secrets and variables → Actions): las variables `VAEL_ROL_GITHUB` y `VAEL_ROL_CFN`, con las salidas de la pila; opcionalmente `CORREO_ALARMAS`; y los secretos `GEMINI_API_KEY` y `SEED_PASSWORD`.

## Seguridad

- El ALB solo acepta tráfico de CloudFront (lista de prefijos administrada) y solo reenvía si llega la cabecera `X-Origen-Vael`.
- El backend solo recibe tráfico del ALB; RDS, solo del backend, y está en subredes sin salida a internet.
- Los buckets son privados: CloudFront lee los sitios con OAC y el backend lee y escribe los CV con el rol de la tarea.
- `DEBUG=false` en producción (sin `/docs`). La URL del administrador de la base y la contraseña de las semillas solo llegan a la tarea de preparación, no al servicio.

## Pendiente

- SES (HU-24): sin el dominio verificado, los correos no se envían en AWS. El error queda en el log y las decisiones se registran igual.
- SES (HU-24): el dominio `vael.work` está registrado en SES (2026-11-08) con DKIM y SPF en GoDaddy; falta salir del sandbox.
