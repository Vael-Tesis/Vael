> COPIA del documento del Drive `VAEL/Docs/06_api_endpoints.md`, versión 2.2, copiada el 2026-10-28.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 06 — API: Endpoints

| Campo | Valor |
|---|---|
| Versión | 2.2 |
| Actualizado | 2026-10-27 |
| Fuente de verdad | Código en `backend/app/routers/` (83 rutas en 9 routers, contadas en `frontend/openapi.json` al cierre del Sprint 1) + DEC-001, DEC-008 a DEC-015, DEC-018, DEC-021 + doc 15 |
| Copia en el repositorio | `docs/diseno/06_api_endpoints.md` (DEC-019). La fuente es este documento |

## Alcance de este documento

Describe **qué endpoints existen o se planifican, quién puede usarlos y qué cambia por las decisiones**. El contrato detallado (campos de cada request y response) es el OpenAPI de FastAPI. Se exporta a `frontend/openapi.json` con `python -m app.scripts.exportar_openapi` y de ahí se genera el cliente tipado del frontend (`npm run api:generar`, DEC-008). El CI falla si el contrato commiteado no coincide con el backend (DEV-C-09 · PR #16).

Estados: **Implementado** · **Ajustado (tarea · PR)**, cambio ya aplicado a una ruta existente · **Cambia (tarea · historia)**, cambio planificado · **Planificado (tarea · historia)**. Lo integrado en el Sprint 1 indica la tarea y el PR.

Prefijo `/api`, sin barra final. Base en desarrollo: `http://localhost:8000`. En producción, CloudFront enruta `/api/*` al balanceador (DEC-018).

## Convenciones

**Autenticación:** `Authorization: Bearer {token}`.

| Token | Emisión | Duración |
|---|---|---|
| RRHH (access) | Login y refresh | **15 minutos** (DEC-011, implementado en DEV-A-02); PyJWT, solo HS256, `exp` obligatorio; claims `sub`, `tenant_id`, `rol`, `type: access`, `ver` |
| RRHH (refresh) | Login y refresh | 7 días; rota en cada uso y queda en `sesiones` (DEC-011) |
| Candidato | Al confirmar RRHH un avance (DEC-009) | 48 horas |

**Aislamiento:** todo endpoint autenticado opera solo sobre el `tenant_id` del token, reforzado con RLS (DEC-010, implementada en DEV-C-11 · PR #10). Solo cinco operaciones cruzan empresas con la sesión del sistema: login, postulación pública por código, listado público de vacantes, feed XML (DEC-014) y resolución del código del candidato (DEC-021).

**Niveles de permiso:** Público · Candidato · Autenticado (cualquier rol de RRHH) · Reclutador+ (`admin`, `gerente`, `reclutador`) · Admin o gerente · Admin · **Interno** (solo las Lambdas, con firma HMAC).

**Regla de decisiones (DEC-009):** ningún endpoint lleva a un candidato a un estado de avance o descarte sin pasar por el endpoint de decisiones.

---

## /api/auth

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| POST | `/auth/login` | Público (sesión del sistema) | Implementado (DEV-A-02 · PR #18): crea una fila en `sesiones`. 401 si las credenciales no son válidas; 403 si el usuario está inactivo |
| POST | `/auth/refresh` | Refresh token válido | Implementado (DEV-A-02): `{ "refresh_token" }`; devuelve un par nuevo y rota el refresh token. Si recibe uno revocado, revoca todas las sesiones del usuario (401) |
| POST | `/auth/logout` | Autenticado | Implementado (DEV-A-02): `{ "refresh_token" }` en el cuerpo; revoca esa sesión |
| GET | `/auth/perfil` | Autenticado | Implementado |
| POST | `/auth/usuarios/crear` | Admin | Implementado (contraseña temporal por SES) |
| GET | `/auth/usuarios` | Admin o gerente | Implementado |
| PUT | `/auth/usuarios/{id}/activar` | Admin | Implementado |
| PUT | `/auth/usuarios/{id}/desactivar` | Admin | Implementado. Incrementa `token_version` y revoca sus sesiones (DEV-A-02): el acceso se corta al instante |
| PUT | `/auth/usuarios/{id}/cambiar-password` | Admin | Implementado. Incrementa `token_version` y revoca sus sesiones (DEV-A-02) |
| POST | `/auth/usuarios/{id}/reenviar-credenciales` | Admin | Implementado |

## /api/areas

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/areas` | Autenticado | Implementado |
| POST | `/areas` | Admin o gerente | Implementado. 409 si el `codigo_corto` ya existe en la empresa (DEV-A-01) |
| GET | `/areas/{id}` | Autenticado | Implementado |
| PUT | `/areas/{id}` | Admin o gerente | Implementado. Misma regla del código corto |
| POST | `/areas/{id}/activar` | Admin o gerente | Implementado (DEV-A-01 · PR #17) |
| POST | `/areas/{id}/desactivar` | Admin o gerente | Implementado (DEV-A-01 · PR #17) |
| DELETE | `/areas/{id}` | Admin | Implementado (DEV-A-01 · PR #17): solo si no tiene vacantes (409 si tiene) |

## /api/plantillas

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/plantillas` | Autenticado | Implementado |
| POST | `/plantillas` | Admin o gerente | Implementado |
| GET | `/plantillas/{id}` | Autenticado | Implementado |
| PUT | `/plantillas/{id}` | Admin o gerente | Implementado. **Ampliado (DEV-A-03 · PR #19):** acepta `dimensiones` opcional para reemplazar todas las dimensiones en una sola operación |
| POST | `/plantillas/{id}/dimensiones` | Admin o gerente | Implementado |
| PUT | `/plantillas/{id}/dimensiones/{dim_id}` | Admin o gerente | Implementado |
| DELETE | `/plantillas/{id}/dimensiones/{dim_id}` | Admin o gerente | Implementado |

Regla: la suma de los pesos de una plantilla debe ser 100. Se valida en **toda** ruta que modifique la plantilla o sus dimensiones; si no suma 100 responde 422 con un mensaje claro (DEV-A-03, CA-06).

## /api/vacantes

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/vacantes` | Autenticado | Implementado |
| POST | `/vacantes` | Reclutador+ | Implementado (crea en borrador; código automático) |
| GET | `/vacantes/{id}` | Autenticado | Implementado |
| PUT | `/vacantes/{id}` | Reclutador+ | Implementado |
| DELETE | `/vacantes/{id}` | Reclutador+ | Implementado (DEV-A-04 · PR #20): solo en borrador y sin candidatos (409 en otro caso) |
| POST | `/vacantes/{id}/publicar`, `/pausar`, `/cerrar`, `/duplicar` | Reclutador+ | Implementado. **Ajustado (DEV-A-04 · PR #20):** 409 si la transición no es válida; `cerrada` es final (ver doc 05) |
| POST | `/vacantes/{id}/generar-textos` | Reclutador+ | Implementado. **Ajustado (DEV-A-04 · PR #20, CA-10):** 502 si la IA falla, sin modificar la vacante |
| GET | `/vacantes/{id}/textos` | Autenticado | Implementado (DEV-A-04 · PR #20): textos guardados |
| PUT | `/vacantes/{id}/textos` | Reclutador+ | Implementado (DEV-A-04 · PR #20): guarda los textos editados |
| GET | `/vacantes/{id}/feed-xml` | Público (sesión del sistema, DEC-014) | Implementado. Solo vacantes abiertas y no confidenciales; 404 en otro caso |

## /api/candidatos

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/candidatos` | Autenticado | Implementado. Filtro `tag_id` con `candidato_tags` (DEV-C-05 · PR #12) |
| POST | `/candidatos` | Reclutador+ | Implementado. **Ajustado (DEV-A-05 · PR #21):** 422 si el archivo no es un PDF válido; 502 si falla el almacenamiento |
| GET | `/candidatos/{id}` | Autenticado | Implementado. Incluye el historial de decisiones (DEV-C-10) y las etiquetas (DEV-A-01) |
| PUT | `/candidatos/{id}` | Reclutador+ | Implementado |
| POST | `/candidatos/{id}/analizar` | Reclutador+ | Implementado. Deja `cv_por_confirmar` con una recomendación (DEC-009, DEV-C-10); se ejecuta con `despachar_tarea` (DEC-016) |
| POST | `/candidatos/carga-masiva` | Reclutador+ | Implementado. Mismo comportamiento; la respuesta incluye `fallidos` con el archivo y el motivo (DEV-A-05 · HU-11) |
| POST | `/candidatos/{id}/cambiar-estado` | Reclutador+ | Implementado. Rechaza los estados de decisión humana con 422 (DEV-C-10) |
| ~~POST~~ | ~~`/candidatos/{id}/marcar-finalista`~~ | — | **Eliminado (DEV-C-10 · PR #13):** se reemplaza por la decisión de la etapa `entrevista` |
| POST | `/candidatos/{id}/reenviar-correo-etapa` | Reclutador+ | Implementado. A un descartado solo el correo de cierre (DEC-013); cubre también `examen_aprobado` (DEV-A-05) |
| GET | `/candidatos/{id}/notas` | Autenticado | Implementado |
| POST | `/candidatos/{id}/notas` | Autenticado | Implementado |
| PUT | `/candidatos/{id}/notas/{nota_id}` | Autor de la nota | Implementado (DEV-A-01 · PR #17). La respuesta incluye `autor_nombre` y `updated_at` |
| DELETE | `/candidatos/{id}/notas/{nota_id}` | Autor o admin | Implementado (DEV-A-01 · PR #17) |
| POST | `/candidatos/{id}/tags` | Reclutador+ | Implementado (DEV-A-01 · PR #17): `{ "tag_id" }`, idempotente |
| DELETE | `/candidatos/{id}/tags/{tag_id}` | Reclutador+ | Implementado (DEV-A-01 · PR #17) |
| POST | `/candidatos/{id}/banco-talento` | Reclutador+ | **Planificado (DEV-A-08 · HU-14)** |
| GET | `/candidatos/ranking` | Autenticado | Implementado. Fórmula de DEC-007 (DEV-C-01 · PR #4). **Cambia (DEV-A-06 · HU-17):** proceso incompleto aparte |
| GET | `/candidatos/banco-talento` | Autenticado | Implementado. **Cambia (DEV-A-08 · HU-14):** filtro por área |

### Decisiones — Implementado (DEV-C-10 · PR #13; HU-15, HU-16; DEC-009 y DEC-013)

| Método | Ruta | Permiso | Función |
|---|---|---|---|
| GET | `/candidatos/por-confirmar?vacante_id=&etapa=` | Reclutador+ | Bandeja de recomendaciones pendientes; incluye el `semaforo` de proctoring (DEV-A-05) |
| POST | `/candidatos/{id}/decision` | Reclutador+ | Decisión individual |
| POST | `/candidatos/decisiones/lote` | Reclutador+ | Confirmación en lote; solo decisiones que coinciden con la IA |
| GET | `/candidatos/{id}/decisiones` | Autenticado | Historial; incluye `decidido_por_nombre` (DEV-A-05) |

Request ilustrativo de decisión individual:

```json
{ "etapa": "cv", "decision": "avanzar", "justificacion_humana": null, "revision_inicio": "2026-10-20T15:02:11Z" }
```

Reglas: justificación obligatoria si la decisión no coincide con la IA (422 si falta); repetir la decisión vigente es idempotente; cambiarla = decisión nueva enlazada con `reemplaza_a`; avance → estado, token y correo de la etapa siguiente; descarte → estado, invalidación de los tokens del candidato y un único correo de cierre. El lote es todo o nada. `revision_inicio` con zona horaria se normaliza a UTC.

**Pendiente de decisión (HU-18, DEV-A-06):** en la etapa `entrevista` no hay umbral, así que el lote no tiene recomendación con la cual coincidir. Propuesta: usar `top_candidatos_finalistas` como criterio, registrada en un ADR nuevo (DEC-022).

## /api/tags — Implementado (DEV-A-01 · PR #17 · HU-13)

| Método | Ruta | Permiso | Función |
|---|---|---|---|
| GET | `/tags` | Autenticado | Lista las etiquetas de la empresa |
| POST | `/tags` | Reclutador+ | `{ "nombre": str(≤50), "color": "#RRGGBB" }`; 409 si el nombre existe |
| PUT | `/tags/{id}` | Reclutador+ | Edita nombre o color |
| DELETE | `/tags/{id}` | Admin o gerente | Elimina la etiqueta y sus asignaciones |

## /api/metricas — Planificado (DEV-A-10 · HU-20)

| Método | Ruta | Permiso | Función |
|---|---|---|---|
| GET | `/metricas/dashboard?desde=&hasta=` | Autenticado | Vacantes y candidatos por estado, recomendaciones pendientes, postulaciones por día, minutos promedio de revisión (OE1) y tasa de concordancia (M-02) |

## /api/evaluaciones

RRHH: `GET /evaluaciones/examenes`, `GET /evaluaciones/examenes/{id}`, `GET /evaluaciones/examenes/{id}/auditoria`, `GET /evaluaciones/auditoria` — Autenticado — Implementados.

Candidato: `POST /evaluaciones/candidato/resolver-codigo` (público), `acceso`, `examen/iniciar`, `examen/respuesta`, `examen/evento`, `GET progreso` (token de candidato) — Implementados. `POST /evaluaciones/candidato/examen/finalizar` — Implementado. Deja `examen_por_confirmar` (DEV-C-10 · PR #13); no aprueba, rechaza ni envía invitaciones.

## /api/entrevista

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/entrevista` | Autenticado | Implementado (listado). La pantalla aún en JavaScript lo llama como `/entrevista/lista`, ruta inexistente: se corrige al migrarla (DEV-A-07 · HU-19). El cliente tipado ya impide ese error (DEC-008) |
| GET | `/entrevista/detalle/{id}` | Autenticado | Implementado |
| POST | `/entrevista/acceso`, `/iniciar`, `/finalizar`, `/captura`, `/evento` | Candidato | Implementados. Sin análisis de sentimiento ni de emociones (DEC-001); revisión completa en el ciclo siguiente |

## /api/interno — Planificado (DEV-C-13 · HU-23, DEC-018)

Endpoints que **solo** usan las Lambdas para entregar sus resultados. Excluidos del OpenAPI público.

| Método | Ruta | Función |
|---|---|---|
| POST | `/interno/resultados/analisis-cv` | Recibe el resultado del análisis de un CV |
| POST | `/interno/resultados/analisis-entrevista` | Recibe el resultado del análisis de una entrevista |

Reglas: firma HMAC-SHA256 del cuerpo y de una marca de tiempo con un secreto de Secrets Manager; rechazo de peticiones con más de 5 minutos; el backend fija el `tenant_id` del mensaje, persiste con RLS y verifica la idempotencia.

## /api/publico

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/publico/postular/{codigo}` | Público (sesión del sistema) | Implementado |
| POST | `/publico/postular/{codigo}/enviar` | Público (sesión del sistema) | Implementado. Aviso previo de IA en el ciclo siguiente |
| GET | `/publico/vacantes` | Público (sesión del sistema) | Implementado |

## /health

`GET /health` — Público — Implementado (health check del balanceador).

## Alta de empresa

No es un endpoint: `python -m app.scripts.crear_empresa` (DEC-015).

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1 | 2026-09-15 | Versión inicial |
| 2.0 | 2026-10-13 | Alineado con las 57 rutas reales; decisiones planificadas |
| 2.1 | 2026-10-18 | 16 endpoints nuevos de la retrospectiva (doc 15): eliminar vacante en borrador, textos de publicación, editar y eliminar notas, etiquetas, banco de talento, activar, desactivar y eliminar áreas, métricas; endpoints internos de las Lambdas (DEC-018); feed XML en la lista cerrada (DEC-014); alta de empresa por script (DEC-015); referencias a historias de usuario |
| 2.2 | 2026-10-27 | Cierre del Sprint 1 (83 rutas): pasan a implementados auth con sesiones, áreas, tags, notas, decisiones, textos y eliminación de vacantes. `marcar-finalista` eliminado. Ampliación de `PUT /plantillas/{id}` con `dimensiones`. Códigos 401/403/409/422/502 documentados. Resolución del código del candidato en la lista cerrada (DEC-021). Pendiente: lote de la etapa entrevista (DEC-022) |
