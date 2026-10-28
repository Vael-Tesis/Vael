# DEC-011 — Autenticación: JWT propio reforzado; Cognito como trabajo futuro

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-02 (decisión 4) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Reemplaza | Docs 01, 04 y `CLAUDE.md` ("Cognito + JWT con tenant claims") |
| Coherente con | Doc 03, roadmap técnico: migración a Cognito posterior a la tesis |
| Relacionada con | DEC-010 (la tabla `sesiones` lleva RLS); DEC-012 (Redis fuera del alcance) |

## Contexto

Estado del código al 2026-10-13 (HECHOS):
- JWT propio firmado con HS256 mediante `python-jose[cryptography]==3.3.0`. Access token de 60 minutos y refresh token de 7 días, sin almacenamiento en el servidor.
- `POST /api/auth/logout` no invalida ningún token; el propio código lo documenta.
- `get_current_user` consulta al usuario en la base de datos en cada petición.
- Los tokens de candidato son JWT de 48 horas con código corto alternativo.
- No hay integración con Cognito ni con Redis.

Evidencia externa: `python-jose` hasta la versión 3.3.0 está afectado por CVE-2024-33663 (confusión de algoritmos con claves ECDSA de OpenSSH) y CVE-2024-33664 (denegación de servicio con tokens JWE comprimidos); ambos se corrigieron en la versión 3.4.0.

Los documentos del proyecto se contradicen: los docs 01 y 04 y `CLAUDE.md` afirman que se usa Cognito; el doc 03 lo ubica como trabajo posterior a la tesis.

## Decisión

1. **Librería:** reemplazar `python-jose` por `PyJWT`. VAEL solo usa JWS con HS256; no necesita el resto de la superficie JOSE (JWE, JWK) que expone `python-jose`.
2. **Access token de 15 minutos** con los claims `sub`, `tenant_id`, `rol`, `type: access` y `ver` (versión de token).
3. **Refresh tokens con estado en PostgreSQL**, tabla `sesiones` con RLS (DEC-010):

   | Campo | Contenido |
   |---|---|
   | `id`, `tenant_id`, `usuario_id` | Identificación |
   | `token_hash` | Hash del refresh token (nunca el token en claro) |
   | `creado_en`, `expira_en`, `revocado_en` | Ciclo de vida |
   | `reemplazado_por` | Sesión que la sustituyó en la rotación |

   - **Rotación:** cada renovación revoca el refresh token usado y emite uno nuevo.
   - **Detección de reutilización:** si se presenta un refresh token ya revocado, se revocan todas las sesiones activas del usuario.
   - **Logout:** revoca el refresh token de la sesión.
4. **Revocación inmediata:** campo `token_version` en `Usuario`. Se incrementa al desactivar al usuario o al cambiar su contraseña. `get_current_user` rechaza todo token cuyo claim `ver` no coincida, sin costo adicional porque ya consulta al usuario en cada petición.
5. **Tokens de candidato sin cambios:** JWT de 48 horas y código corto `VAEL-XXXX-XXXX`, con la nueva librería.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Amazon Cognito en este ciclo | 2 a 3 días de trabajo (User Pool, Lambda de pre-generación de tokens para `tenant_id`, flujo de contraseña temporal, emulación local) con riesgo alto para el plazo de E3; los candidatos seguirían usando tokens propios, con dos sistemas de autenticación en paralelo |
| Mantener `python-jose` actualizado a 3.4.0 o superior | Corrige las vulnerabilidades conocidas y es una alternativa aceptable; se prefiere PyJWT por limitarse a lo que VAEL usa. Si la migración presentara problemas, esta es la alternativa de respaldo |
| Refresh tokens sin estado (situación actual) | El logout no tiene efecto real y no hay forma de revocar una sesión comprometida |

## Trade-off aceptado

- Tras un logout, el access token sigue siendo válido hasta su expiración: como máximo 15 minutos. No aplica a la desactivación de usuarios ni al cambio de contraseña, cubiertos por `token_version`.
- VAEL no incorpora Cognito como evidencia de uso de AWS. Se justifica porque la plataforma ya usa ECS, RDS, S3, SES, Rekognition y Secrets Manager, y porque Cognito no resolvería un problema que hoy no esté resuelto. La migración queda como trabajo futuro.

## Consecuencias

Cambios en el roadmap:

| Tarea | Cambio |
|---|---|
| DEV-A-02 (redefinida) | Migración a PyJWT, access de 15 minutos, tabla `sesiones` con rotación y detección de reutilización, logout efectivo y `token_version`. El frontend renueva el access token de forma transparente con el refresh token |

Documentos a actualizar:
- Docs 01 y 04 y `CLAUDE.md`: eliminar la afirmación de que se usa Cognito.
- Doc 03: aclarar el estado actual y mantener Cognito en el roadmap posterior a la tesis.
- Doc 05: tabla `sesiones` y campo `token_version`.
- Doc 06: comportamiento de `/auth/refresh` y `/auth/logout`.
- Doc 09: eliminar Cognito del orden de aprovisionamiento y `REFRESH_TOKEN_EXPIRE_DAYS` según corresponda; `ACCESS_TOKEN_EXPIRE_MINUTES=15`.

## Validación

- Test: tras el logout, el refresh token de esa sesión es rechazado.
- Test: un refresh token usado dos veces provoca la revocación de todas las sesiones del usuario.
- Test: al desactivar un usuario, su access token vigente es rechazado en la siguiente petición.
- Test: la tabla `sesiones` nunca guarda el token en claro.
- Test: un token firmado con otro algoritmo o con `alg: none` es rechazado.
