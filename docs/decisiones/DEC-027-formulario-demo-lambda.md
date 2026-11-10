# DEC-027 — Formulario de demo de la landing con una Lambda permanente y SES

| Campo | Valor |
|---|---|
| Estado | Propuesta |
| Fecha | 2026-11-10 |
| Tarea de origen | DEP-C-07 (pedido del Product Owner) |
| Propuesto por | Gabriel Llanos (Product Owner); registrada por Gabriel Llanos |
| Relacionada con | DEC-018 (topología AWS y entorno temporal), HU-24 (dominio y SES) |

## Contexto

- **HECHO:** el formulario «Solicitar demo» de `www.vael.work` abría el correo del visitante con un mensaje armado (`mailto:`). La solicitud solo llegaba si el visitante terminaba de enviarla desde su cliente de correo.
- **HECHO:** el Product Owner pidió que el visitante escriba su correo y reciba uno automáticamente.
- **HECHO:** la landing es estática (S3 + CloudFront, pila permanente `vael-base`). El backend de VAEL solo está encendido durante las demos (decisión del 2026-10-25), así que un endpoint del backend dejaría el formulario sin funcionar la mayor parte del tiempo.
- **HECHO:** `vael.work` está verificado en SES (2026-11-08), pero la cuenta sigue en *sandbox*. Mientras no se apruebe el acceso de producción, SES solo entrega a direcciones verificadas.
- **HECHO:** `contacto@vael.work` existe en Zoho Mail y recibe correo (2026-11-10).

## Decisión

1. **Una Lambda permanente (`vael-contacto`) en la pila `vael-base`, con URL pública.** Recibe `{correo}` desde la landing y envía dos correos por SES desde `VAEL <contacto@vael.work>`:
   - **al visitante:** la confirmación de la solicitud y qué datos enviar para preparar la demo; si responde, la respuesta llega a `contacto@vael.work`;
   - **al equipo:** un aviso con el correo del visitante; si se responde, la respuesta va al visitante.
2. **No toca la base de datos ni el backend** y no guarda datos: el único registro es el correo que queda en la bandeja de `contacto@vael.work`.
3. **Protecciones contra el abuso** (el formulario podría usarse para enviar correos a terceros):
   - el contenido es fijo y el visitante solo aporta su dirección;
   - solo se aceptan peticiones con origen `www.vael.work` o `vael.work` (CORS y verificación en el código);
   - un campo trampa invisible: si llega lleno, se responde sin enviar nada;
   - un tope de 20 envíos por instancia cada 10 minutos;
   - el rol de la Lambda solo puede usar `ses:SendEmail` con remitente `contacto@vael.work`.
4. **La landing lee la URL de `config.js`.** El despliegue lo genera a partir de la salida `ContactoUrl` de la pila. Si no existe o el envío falla, se vuelve a abrir el correo del visitante con la solicitud armada.
5. **El código vive inline en la plantilla** (menos de 4096 caracteres). Lo prueba `backend/tests/test_formulario_demo.py` con un cliente de SES falso.

## Consecuencias

- **Disponibilidad:** el formulario funciona siempre, aunque el entorno esté apagado, sin costo fijo. Lambda y SES cuestan fracciones de centavo con este uso.
- **Hasta salir del *sandbox* de SES:** solo funciona con direcciones verificadas en SES. Con cualquier otra, la Lambda responde 502 y la landing abre el correo del visitante (plan B). El Product Owner solicita el acceso de producción.
- **Pila permanente con IAM:** `vael-base` pasa a crear un rol de IAM (`vael-base-RolContacto-*`), así que su despliegue requiere `CAPABILITY_IAM`. El rol de servicio `vael-cloudformation` ya permite roles `vael-base-*`.
- **Tope por instancia:** el límite no es global. Si hay abuso a gran escala, el siguiente paso es un captcha (por ejemplo, Cloudflare Turnstile) o un límite por dirección con almacenamiento.
- **Datos personales:** el correo del visitante se envía a él mismo y al buzón del equipo. La política de privacidad de la landing ya indica `contacto@vael.work` como canal.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Mantener `mailto:` | El Product Owner pidió el envío automático |
| Endpoint en el backend de VAEL | El backend está apagado la mayor parte del tiempo (DEC-018) |
| Servicio externo de formularios (Formspree, Web3Forms) | La respuesta automática al visitante suele ser de pago y los datos pasan por un tercero |
