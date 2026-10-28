# DEC-023 — S3 y correo locales para desarrollo: Adobe S3Mock y Mailpit

| Campo | Valor |
|---|---|
| Estado | Aprobada por el Product Owner; pendiente de revisión del equipo en el PR |
| Fecha | 2026-10-28 |
| Tarea de origen | TST-A-01 (prueba manual del perfil Admin) |
| Decidido por | Gabriel Llanos (Product Owner) |
| Modifica | Solo el entorno de desarrollo (`docker-compose.yml`); no cambia DEC-016 ni DEC-018 |

## Contexto

Registrar un candidato o enviar una postulación sube el CV a S3. En desarrollo no hay S3: sin credenciales de AWS la subida falla, y la postulación pública respondía 500. Eso impedía probar en local RF-A-09 a RF-A-12 (registro, análisis, bandeja e historial) y las pruebas E2E de TST-A-03.

Los correos de desarrollo salen por SMTP a `localhost:1025`, pero no había nada escuchando ahí, así que no se podía verificar el correo de avance ni el único correo de cierre (DEC-013, RF-A-11).

El Product Owner aprobó MinIO como S3 local el 2026-10-28. Al implementarlo, ninguna imagen de MinIO se pudo descargar: ya no se publican en Docker Hub y quay.io rechaza la descarga. El Product Owner eligió el reemplazo.

## Decisión

1. **Adobe S3Mock** (`adobe/s3mock`, versión fijada) como S3 local en `docker-compose`. Crea el bucket `vael-storage` al arrancar y guarda los archivos en un volumen.
2. La variable **`S3_ENDPOINT_URL`** activa el S3 local. Con ella, el cliente de S3 usa rutas `endpoint/bucket/clave` y credenciales de relleno, para no firmar nunca con una cuenta real. Vacía, que es el caso en AWS, todo sigue como antes.
3. **Mailpit** (`axllent/mailpit`, versión fijada) captura los correos de desarrollo: SMTP en el puerto 1025 y bandeja web en `http://localhost:8025`.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| MinIO | Sin imágenes descargables (ver Contexto) |
| LocalStack | Emula también SES y SQS, pero es más pesado y sus versiones recientes tienden a exigir cuenta o token |
| SeaweedFS | El más parecido a MinIO, pero necesita más configuración (servicios, credenciales y bucket) |
| Un bucket real de S3 para desarrollo | Costo, credenciales en cada máquina, y contradice la decisión de usar AWS solo cuando se va a usar |

## Trade-off aceptado

S3Mock no aplica permisos ni políticas de bucket: cualquiera con la URL lee el archivo. Sirve para desarrollar y probar, no para verificar la seguridad de S3. Eso se valida en AWS (HU-22).

## Consecuencias

- `docker-compose.yml`: servicios `s3mock` y `mailpit`; el backend del compose los usa.
- `backend/.env.example`: `S3_ENDPOINT_URL=http://localhost:9090`; los valores SMTP existentes ya apuntan a Mailpit.
- El envío por SMTP sin usuario ya no intenta STARTTLS: con `SMTP_USER=` vacío fallaba contra cualquier servidor local.
- Doc 04 (stack) y doc 09 (variables de entorno) del Drive: agregar S3Mock, Mailpit y `S3_ENDPOINT_URL`.
- Hallazgo pendiente, no resuelto por esta decisión: el análisis descarga el CV por HTTP desde `cv_url`. Con el bucket privado de AWS, que solo da acceso por URL prefirmada (doc 03), esa descarga recibirá 403. Se resuelve en HU-22 o HU-23.

## Validación

- Subida y descarga contra S3Mock con un nombre de archivo con espacios.
- Un correo enviado con la configuración de `.env.example` aparece en la bandeja de Mailpit.
- Prueba automática: la postulación pública rechaza un PDF dañado (422), responde 502 con mensaje si S3 falla y crea el candidato cuando la subida funciona.
