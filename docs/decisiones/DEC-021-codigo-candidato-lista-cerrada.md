# DEC-021 — Resolución del código del candidato en la lista cerrada de operaciones del sistema

| Campo | Valor |
|---|---|
| Estado | Aprobada (Product Owner; revisión del equipo en el PR #10 de DEV-C-11, 2026-10-25) |
| Fecha | 2026-10-25 |
| Tarea de origen | DEV-C-11 (hallazgo al aplicar la RLS) |
| Decidido por | Gabriel Llanos (Product Owner) |
| Modifica | DEC-010, punto 5, y DEC-014 (lista cerrada de operaciones del sistema) |

## Contexto

DEC-010 limitó la sesión del sistema (`vael_system`, con `BYPASSRLS`) a una lista cerrada de operaciones, y DEC-014 la amplió a cuatro: login, postulación pública por código, listado público de vacantes y feed XML. Cualquier otra ampliación requiere un ADR.

Al implementar la RLS (DEV-C-11) apareció un quinto endpoint público: `POST /api/evaluaciones/candidato/resolver-codigo`. El candidato escribe el código corto que recibió por correo (`VAEL-XXXX-XXXX`) y el endpoint responde con el JWT asociado. No recibe token, así que no hay `tenant_id` que fijar; con la RLS activa, la búsqueda devuelve cero filas y el candidato no puede ingresar por código.

## Decisión

`POST /api/evaluaciones/candidato/resolver-codigo` se agrega a la lista cerrada de DEC-010 y usa la sesión del sistema, con estas restricciones:
- Solo lectura: no modifica ningún registro.
- Busca un único registro de `tokens_acceso` por `codigo_corto`, que es único en toda la plataforma.
- Responde únicamente con el JWT asociado. El JWT ya lleva el `tenant_id`, así que las peticiones siguientes del candidato pasan por la sesión normal con su tenant fijado.
- Si el código no existe, ya se usó o expiró, responde con error sin revelar datos de la empresa.

La lista cerrada queda en cinco operaciones: login, postulación pública por código, listado público de vacantes, feed XML y resolución del código del candidato.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Incluir un prefijo de la empresa en el código | Cambia el formato del código, los correos y el flujo del doc 07 sin un beneficio de seguridad: el código ya es único y no adivinable |
| Quitar el ingreso manual del código | Obliga a entrar solo por el enlace del correo; empeora la experiencia del candidato cuando el enlace no abre (correo corporativo, otro dispositivo) |

## Trade-off aceptado

Una operación más queda protegida solo por la capa de aplicación. El riesgo es bajo: es de solo lectura, devuelve un único registro por un código único y solo expone el JWT que el propio candidato ya recibió por correo.

## Consecuencias

- DEV-C-11: la ruta usa `get_system_db` y entra en el test que verifica qué operaciones usan la sesión del sistema.
- `CLAUDE.md`: la regla multiempresa 4 lista las cinco operaciones.
- Doc 03, doc 05 y su copia en `docs/diseno/`: la lista cerrada pasa a tener cinco operaciones.
- Doc 06 y su copia en `docs/diseno/`: la ruta se marca como "Público (sesión del sistema)".

## Validación

- Test: con la RLS activa, un código válido de otra empresa se resuelve y devuelve su JWT.
- Test: solo las cinco operaciones de la lista cerrada dependen de la sesión del sistema.
