> COPIA del documento del Drive `VAEL/Docs/06_api_endpoints.md`, versión 2.1, copiada el 2026-10-18.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 06 — API: Endpoints

| Campo | Valor |
|---|---|
| Versión | 2.1 |
| Actualizado | 2026-10-18 |
| Fuente de verdad | Código en `backend/app/routers/` (57 rutas en 8 routers, revisadas el 2026-10-13) + DEC-001, DEC-009 a DEC-015, DEC-018 + doc 15 |
| Copia en el repositorio | `docs/diseno/06_api_endpoints.md` (DEC-019). La fuente es este documento |

## Alcance de este documento

Describe **qué endpoints existen o se planifican, quién puede usarlos y qué cambia por las decisiones**. El contrato detallado (campos de cada request y response) es el OpenAPI de FastAPI (`/openapi.json`), que también genera el cliente tipado del frontend (DEC-008).

Estados: **Implementado** · **Cambia (tarea · historia)** · **Planificado (tarea · historia)**.

Prefijo `/api`, sin barra final. Base en desarrollo: `http://localhost:8000`. En producción, CloudFront enruta `/api/*` al balanceador (DEC-018).

## Convenciones

**Autenticación:** `Authorization: Bearer {token}`.

| Token | Emisión | Duración |
|---|---|---|
| RRHH (access) | Login y refresh | **15 minutos** con DEC-011 (hoy 60); claims `sub`, `tenant_id`, `rol`, `type: access`, `ver` |
| RRHH (refresh) | Login y refresh | 7 días; rota en cada uso y queda en `sesiones` (DEC-011) |
| Candidato | Al confirmar RRHH un avance (DEC-009) | 48 horas |

**Aislamiento:** todo endpoint autenticado opera solo sobre el `tenant_id` del token, reforzado con RLS (DEC-010). Solo cuatro operaciones cruzan empresas con la sesión del sistema: login, postulación pública por código, listado público de vacantes y feed XML (DEC-014).

**Niveles de permiso:** Público · Candidato · Autenticado (cualquier rol de RRHH) · Reclutador+ (`admin`, `gerente`, `reclutador`) · Admin o gerente · Admin · **Interno** (solo las Lambdas, con firma HMAC).

**Regla de decisiones (DEC-009):** ningún endpoint lleva a un candidato a un estado de avance o descarte sin pasar por el endpoint de decisiones.

---

## /api/auth

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| POST | `/auth/login` | Público (sesión del sistema) | Implementado. **Cambia (DEV-A-02 · HU-01):** crea una fila en `sesiones` |
| POST | `/auth/refresh` | Refresh token válido | Implementado. **Cambia (DEV-A-02 · HU-02):** rota el refresh token; si recibe uno revocado, revoca todas las sesiones del usuario |
| POST | `/auth/logout` | Autenticado | Implementado. **Cambia (DEV-A-02 · HU-02):** revoca el refresh token |
| GET | `/auth/perfil` | Autenticado | Implementado |
| POST | `/auth/usuarios/crear` | Admin | Implementado (contraseña temporal por SES) |
| GET | `/auth/usuarios` | Admin o gerente | Implementado |
| PUT | `/auth/usuarios/{id}/activar` | Admin | Implementado |
| PUT | `/auth/usuarios/{id}/desactivar` | Admin | Implementado. **Cambia (DEV-A-02 · HU-07):** incrementa `token_version` |
| PUT | `/auth/usuarios/{id}/cambiar-password` | Admin | Implementado. **Cambia (DEV-A-02):** incrementa `token_version` |
| POST | `/auth/usuarios/{id}/reenviar-credenciales` | Admin | Implementado |

## /api/areas

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/areas` | Autenticado | Implementado |
| POST | `/areas` | Admin o gerente | Implementado |
| GET | `/areas/{id}` | Autenticado | Implementado |
| PUT | `/areas/{id}` | Admin o gerente | Implementado |
| POST | `/areas/{id}/activar` | Admin o gerente | **Planificado (DEV-A-01 · HU-05)** |
| POST | `/areas/{id}/desactivar` | Admin o gerente | **Planificado (DEV-A-01 · HU-05)** |
| DELETE | `/areas/{id}` | Admin | **Planificado (DEV-A-01 · HU-05):** solo si no tiene vacantes (409 si tiene) |

## /api/plantillas

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/plantillas` | Autenticado | Implementado |
| POST | `/plantillas` | Admin o gerente | Implementado |
| GET | `/plantillas/{id}` | Autenticado | Implementado |
| PUT | `/plantillas/{id}` | Admin o gerente | Implementado |
| POST | `/plantillas/{id}/dimensiones` | Admin o gerente | Implementado |
| PUT | `/plantillas/{id}/dimensiones/{dim_id}` | Admin o gerente | Implementado |
| DELETE | `/plantillas/{id}/dimensiones/{dim_id}` | Admin o gerente | Implementado |

Regla: la suma de los pesos de una plantilla debe ser 100.

## /api/vacantes

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/vacantes` | Autenticado | Implementado |
| POST | `/vacantes` | Reclutador+ | Implementado (crea en borrador; código automático) |
| GET | `/vacantes/{id}` | Autenticado | Implementado |
| PUT | `/vacantes/{id}` | Reclutador+ | Implementado |
| DELETE | `/vacantes/{id}` | Reclutador+ | **Planificado (DEV-A-04 · HU-08):** solo en borrador (409 en otro estado) |
| POST | `/vacantes/{id}/publicar`, `/pausar`, `/cerrar`, `/duplicar` | Reclutador+ | Implementado |
| POST | `/vacantes/{id}/generar-textos` | Reclutador+ | Implementado |
| GET | `/vacantes/{id}/textos` | Autenticado | **Planificado (DEV-A-04 · HU-10):** textos guardados |
| PUT | `/vacantes/{id}/textos` | Reclutador+ | **Planificado (DEV-A-04 · HU-10):** guarda los textos editados |
| GET | `/vacantes/{id}/feed-xml` | Público (sesión del sistema, DEC-014) | Implementado. Solo vacantes abiertas y no confidenciales; 404 en otro caso |

## /api/candidatos

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/candidatos` | Autenticado | Implementado. El filtro por tag funciona con `candidato_tags` (DEV-C-05) |
| POST | `/candidatos` | Reclutador+ | Implementado |
| GET | `/candidatos/{id}` | Autenticado | Implementado. **Cambia (DEV-C-10 · HU-16):** incluye el historial de decisiones |
| PUT | `/candidatos/{id}` | Reclutador+ | Implementado |
| POST | `/candidatos/{id}/analizar` | Reclutador+ | Implementado. **Cambia (DEV-C-10):** deja `cv_por_confirmar` con una recomendación; se ejecuta con `despachar_tarea` (DEC-016) |
| POST | `/candidatos/carga-masiva` | Reclutador+ | Implementado. Mismo cambio; informa los archivos fallidos (HU-11) |
| POST | `/candidatos/{id}/cambiar-estado` | Reclutador+ | Implementado. **Cambia (DEV-C-10):** rechaza estados de decisión humana (422) |
| POST | `/candidatos/{id}/marcar-finalista` | Reclutador+ | Implementado. **Se reemplaza (DEV-C-10)** por la decisión de la etapa `entrevista` |
| POST | `/candidatos/{id}/reenviar-correo-etapa` | Reclutador+ | Implementado. **Cambia:** a un descartado solo el correo de cierre (DEC-013) |
| GET | `/candidatos/{id}/notas` | Autenticado | Implementado |
| POST | `/candidatos/{id}/notas` | Autenticado | Implementado |
| PUT | `/candidatos/{id}/notas/{nota_id}` | Autor de la nota | **Planificado (DEV-A-01 · HU-13)** |
| DELETE | `/candidatos/{id}/notas/{nota_id}` | Autor o admin | **Planificado (DEV-A-01 · HU-13)** |
| POST | `/candidatos/{id}/tags` | Reclutador+ | **Planificado (DEV-A-01 · HU-13):** `{ "tag_id" }`, idempotente |
| DELETE | `/candidatos/{id}/tags/{tag_id}` | Reclutador+ | **Planificado (DEV-A-01 · HU-13)** |
| POST | `/candidatos/{id}/banco-talento` | Reclutador+ | **Planificado (DEV-A-08 · HU-14)** |
| GET | `/candidatos/ranking` | Autenticado | Implementado. **Cambia (DEV-C-01, DEV-A-06 · HU-17):** fórmula de DEC-007; proceso incompleto aparte |
| GET | `/candidatos/banco-talento` | Autenticado | Implementado. **Cambia (DEV-A-08 · HU-14):** filtro por área |

### Decisiones — Planificado (DEV-C-10 · HU-15, HU-16, HU-18; DEC-009 y DEC-013)

| Método | Ruta | Permiso | Función |
|---|---|---|---|
| GET | `/candidatos/por-confirmar?vacante_id=&etapa=` | Reclutador+ | Bandeja de recomendaciones pendientes |
| POST | `/candidatos/{id}/decision` | Reclutador+ | Decisión individual |
| POST | `/candidatos/decisiones/lote` | Reclutador+ | Confirmación en lote; solo decisiones que coinciden con la IA |
| GET | `/candidatos/{id}/decisiones` | Autenticado | Historial |

Request ilustrativo de decisión individual:

```json
{ "etapa": "cv", "decision": "avanzar", "justificacion_humana": null, "revision_inicio": "2026-10-20T15:02:11Z" }
```

Reglas: justificación obligatoria si la decisión no coincide con la IA (422 si falta); revertir = decisión nueva enlazada con `reemplaza_a`; avance → estado, token y correo de la etapa siguiente; descarte → estado y un único correo de cierre.

## /api/tags — Planificado (DEV-A-01 · HU-13)

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

Candidato: `POST /evaluaciones/candidato/resolver-codigo` (público), `acceso`, `examen/iniciar`, `examen/respuesta`, `examen/evento`, `GET progreso` (token de candidato) — Implementados. `POST /evaluaciones/candidato/examen/finalizar` — Implementado. **Cambia (DEV-C-10):** deja `examen_por_confirmar`; no aprueba, rechaza ni envía invitaciones.

## /api/entrevista

| Método | Ruta | Permiso | Estado |
|---|---|---|---|
| GET | `/entrevista` | Autenticado | Implementado (listado). El frontend lo llama hoy como `/entrevista/lista`, ruta inexistente: se corrige en HU-19 |
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
