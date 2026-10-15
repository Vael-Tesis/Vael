# DEC-014 — Feed XML de vacantes en la lista cerrada de operaciones del sistema

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-03 (hallazgo al actualizar el doc 06) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Modifica | DEC-010, punto 5 (lista cerrada de operaciones del sistema) |

## Contexto

DEC-010 limitó a tres las operaciones que usan la sesión del sistema (`vael_system`, con `BYPASSRLS`): login, postulación pública por código y listado público de vacantes. Cualquier ampliación requiere un ADR.

Al revisar los permisos de las 57 rutas (doc 06 v2.0) se encontró un cuarto endpoint público: `GET /api/vacantes/{vacante_id}/feed-xml`, que genera el feed XML de una vacante para bolsas de empleo externas (Indeed). No recibe token, por lo que no hay `tenant_id` que fijar; con RLS activa devolvería un resultado vacío.

## Decisión

`GET /api/vacantes/{vacante_id}/feed-xml` se agrega a la lista cerrada de DEC-010 y usa la sesión del sistema, con las mismas restricciones que el listado público de vacantes:
- Solo lectura.
- Solo vacantes en estado `abierta` y con `confidencial = false`; en cualquier otro caso responde 404.
- Expone únicamente los campos públicos de la vacante (los mismos que el formulario público de postulación).

La lista cerrada queda en cuatro operaciones: login, postulación pública por código, listado público de vacantes y feed XML.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Retirar el feed XML del alcance | Elimina un canal de difusión ya implementado sin un motivo de seguridad que lo justifique: expone la misma información que el listado público |
| Exigir autenticación al feed | Las bolsas de empleo consumen el feed sin credenciales de VAEL |

## Trade-off aceptado

Una operación más queda protegida solo por la capa de aplicación. El riesgo es bajo porque es de solo lectura y filtra por las mismas condiciones que el listado público.

## Consecuencias

- DEV-C-11: incluir el feed XML en la sesión del sistema y en el test que verifica qué módulos la usan.
- Doc 03 y doc 05: la lista cerrada pasa a tener cuatro operaciones.
- Doc 06: el feed XML se marca como "Público (sesión del sistema)".

## Validación

- Test: el feed de una vacante abierta y no confidencial responde 200 con sus campos públicos.
- Test: el feed de una vacante en borrador, pausada, cerrada o confidencial responde 404.
- Test: solo los cuatro módulos de la lista cerrada importan la sesión del sistema.
