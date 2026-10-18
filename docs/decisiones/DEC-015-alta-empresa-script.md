# DEC-015 — Alta de empresas cliente mediante un comando de administración

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-14 |
| Tarea de origen | PLN-A-02 (doc 15, revisión R4) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Relacionada con | DEC-010 (lista cerrada de operaciones del sistema) |

## Contexto

El onboarding de una empresa (doc 03) requiere crear el registro en `empresas` con su `tenant_id` y su administrador inicial. No existe un rol de plataforma que pueda autorizar esa operación. El cobro y las suscripciones están fuera del alcance de esta versión (monografía, sección 1.3), por lo que el autoservicio de registro no aporta a ningún objetivo específico.

## Decisión

En esta versión, el alta de empresas se realiza con un **comando de administración** que ejecuta el operador de VAEL, sin endpoint HTTP:

```bash
python -m app.scripts.crear_empresa --nombre "<razón social>" --admin-email <correo>
```

El comando:
1. Genera el `tenant_id` y crea la empresa.
2. Fija ese tenant en la sesión (`app.tenant_id`) y crea al administrador inicial con una contraseña temporal, usando el rol `vael_app`.
3. Envía las credenciales por SES.
4. Es idempotente: si la empresa o el correo ya existen, informa y no duplica.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Endpoint público de registro (autoservicio) | Abre la creación de empresas a cualquiera, exige protección contra abuso y ampliaría la lista cerrada de DEC-010; sin cobro implementado, no aporta valor |
| Rol de superadministrador de plataforma con su propio panel | Nuevo rol, nuevas pantallas y nuevas reglas de aislamiento, sin relación con los objetivos del proyecto |

## Trade-off aceptado

El alta no es autoservicio: depende del equipo de VAEL. Es coherente con el modelo de negocio, que describe un onboarding asistido (doc 02).

## Consecuencias

- DEV-A-01: implementar el script en lugar de un endpoint.
- DEV-C-03 (semillas): reutiliza el script para crear las empresas A y B.
- Doc 06: el alta de empresa deja de figurar como endpoint pendiente.
- Doc 03: el paso 1 del onboarding indica el script.

## Validación

- Test: el script crea la empresa y su administrador, y el administrador puede iniciar sesión.
- Test: ejecutarlo dos veces con los mismos datos no duplica registros.
- Test: el administrador creado solo ve datos de su propia empresa.
