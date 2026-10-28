> COPIA del documento del Drive `VAEL/Docs/05_modelos_bd.md`, versión 2.2, copiada el 2026-10-28.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 05 — Modelos de Base de Datos

| Campo | Valor |
|---|---|
| Versión | 2.2 |
| Actualizado | 2026-10-27 |
| Fuente de verdad | Código en `backend/app/models/` (migraciones hasta `a6b7c8d9e0f1`, Sprint 1) + DEC-007, DEC-009, DEC-010, DEC-011, DEC-014, DEC-015, DEC-018 + doc 15 |
| Copia en el repositorio | `docs/diseno/05_modelos_bd.md` (DEC-019). La fuente es este documento |

Todos los modelos usan SQLModel y residen en `backend/app/models/`, un archivo por dominio. Cada tabla y campo indica su estado:
- **Implementado:** existe en el código y en su migración. Lo integrado en el Sprint 1 indica la tarea y el PR.
- **Planificado (tarea · historia):** definido por una decisión o por el doc 15; se implementa en esa tarea.

## Convenciones generales

- **Claves primarias:** UUID v4 guardado como texto (`str`), generado por `new_id()`. Las claves foráneas también son `str`.
- **Aislamiento (DEC-010):** todas las tablas tienen `tenant_id` (texto de 36 caracteres, indexado) y quedan protegidas en dos capas: el filtro de la aplicación y una política de RLS (*Row-Level Security*, seguridad a nivel de fila) en PostgreSQL.
- **Campos JSON:** tipo `JSON` de SQLAlchemy. Se evaluará `JSONB` si se necesita filtrar por su contenido.
- **Fechas:** en UTC.

## Clases base — Implementado

```python
class TenantBase(SQLModel):
    tenant_id: str = Field(index=True, nullable=False, max_length=36)

class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)
```

## models/usuario.py

### Empresa — `empresas` — Implementado

| Campo | Tipo | Notas |
|---|---|---|
| id | str (UUID) | PK |
| tenant_id | str(36) | Único, indexado |
| nombre | str | |
| logo_url | str? | Key en S3 |
| email_contacto | str(255)? | **Implementado (DEV-C-10 · PR #13).** Contacto de la empresa para datos personales; aparece en el correo de cierre (DEC-013). Nulo: el correo omite la línea |
| activa | bool | Default true |
| created_at | datetime | |

Se crea con el comando `python -m app.scripts.crear_empresa` (DEC-015), nunca por un endpoint.

### Usuario — `usuarios` — Implementado

| Campo | Tipo | Notas |
|---|---|---|
| id | str (UUID) | PK |
| tenant_id | str(36) | |
| nombre, apellidos | str | |
| email | str(255) | Único global, indexado |
| password_hash | str | bcrypt |
| rol | enum | `admin` / `reclutador` / `evaluador` / `gerente` |
| telefono | str? | |
| activo | bool | Default true |
| token_version | int | **Implementado (DEV-A-02 · PR #18).** Default 0. Viaja en el access token como `ver`. Se incrementa al desactivar o cambiar la contraseña; invalida todos los tokens del usuario (DEC-011) |
| created_at, updated_at | datetime | |

Roles: `admin` (todo, usuarios y configuración); `reclutador` (vacantes y candidatos; confirma o revierte recomendaciones); `gerente` (lectura de todo, dashboard; confirma o revierte recomendaciones); `evaluador` (solo lectura de evaluaciones).

### Sesion — `sesiones` — Implementado (DEV-A-02 · PR #18, DEC-011)

| Campo | Tipo | Notas |
|---|---|---|
| id | str (UUID) | PK |
| tenant_id | str(36) | |
| usuario_id | str | FK a `usuarios`, indexado |
| token_hash | str(64) | SHA-256 del refresh token; **nunca el token en claro** |
| creado_en, expira_en | datetime | |
| revocado_en | datetime? | Logout, rotación o detección de reutilización |
| reemplazado_por | str? | FK a `sesiones` |

Cada renovación revoca la sesión usada y crea otra. Presentar un refresh token ya revocado revoca todas las sesiones activas del usuario (detección de reutilización). Tiene RLS.

### TokenAcceso — `tokens_acceso` — Implementado

| Campo | Tipo | Notas |
|---|---|---|
| id | str (UUID) | PK |
| tenant_id | str(36) | |
| candidato_id | str | FK, indexado |
| token | str | Único, indexado. JWT firmado |
| codigo_corto | str(14) | Único. Formato `VAEL-XXXX-XXXX` |
| tipo | enum | `examen` / `entrevista` |
| expira_en | datetime | 48 horas desde la emisión |
| usado | bool | Default false |
| created_at | datetime | |

Se emite solo cuando RRHH confirma un avance (DEC-009).

## models/area.py

### Area — `areas` — Implementado

| Campo | Tipo | Notas |
|---|---|---|
| id | str (UUID) | PK |
| tenant_id | str(36) | |
| nombre | str | |
| codigo_corto | str(10) | Indexado; se usa en el código de vacante |
| descripcion | str? | |
| instruccion_ia | str? | Personaliza el análisis de IA del área |
| activa | bool | Default true |
| created_at, updated_at | datetime | |

Reglas (doc 15, implementadas en DEV-A-01 · PR #17): un área con vacantes no se elimina (409); se desactiva. El `codigo_corto` no se repite dentro de la empresa, sin distinguir mayúsculas (409).

## models/vacante.py

### Vacante — `vacantes` — Implementado

Datos básicos: `id`, `tenant_id`, `area_id` (FK), `codigo` (str(30), único, `{AREA}-{AÑO}-{NNN}`), `titulo`, `descripcion?`, `responsabilidades?`, `requisitos?`, `requisitos_deseables?`, `beneficios?`, `habilidades` (JSON, lista), `tecnologias` (JSON, lista).

Condiciones: `nivel_experiencia?` (`practicante` / `junior` / `semi_senior` / `senior` / `lider`), `anios_experiencia?`, `modalidad?` (`presencial` / `remoto` / `hibrido`), `tipo_contrato?` (`indefinido` / `plazo_fijo` / `practicas` / `freelance` / `part_time`), `ciudad?`, `pais?`, `salario_minimo?`, `salario_maximo?`, `moneda` (default `PEN`), `mostrar_salario` (default false).

Gestión: `confidencial` (bool), `estado` (`borrador` / `abierta` / `pausada` / `cerrada`, indexado), `prioridad` (`baja` / `media` / `alta` / `urgente`, default `media`), `fecha_limite?`, `jefe_directo?`, `solicitante?`, `cantidad_posiciones` (default 1).

Parámetros de IA:

| Campo | Default | Función |
|---|---|---|
| score_cv_minimo | 60 | Umbral de la **recomendación** de la etapa de CV; no ejecuta el descarte (DEC-009) |
| nota_minima_examen | 13 | Umbral de la recomendación de la etapa de examen |
| top_candidatos_finalistas | 5 | Cantidad sugerida de finalistas |
| instruccion_ia_extra | null | Instrucción adicional de la vacante |

Campo nuevo:

| Campo | Tipo | Notas |
|---|---|---|
| textos_publicacion | JSON (objeto)? | **Implementado (DEV-A-04 · PR #20).** Textos de difusión generados por la IA y editados por RRHH, por canal |

Reglas (doc 15, implementadas en DEV-A-04): una vacante solo se elimina en estado `borrador` y sin candidatos (409). Transiciones válidas: `borrador` → `abierta`; `abierta` ↔ `pausada`; `abierta` o `pausada` → `cerrada`. **`cerrada` es final** (pendiente de confirmar por el Product Owner).

## models/candidato.py

### Candidato — `candidatos` — Implementado (+ campo planificado)

Datos personales: `id`, `tenant_id`, `vacante_id` (FK), `nombre`, `apellidos`, `email` (indexado), `telefono?`, `linkedin?`, `github?`, `portfolio?`, `cv_url?` (key en S3), `pretension_salarial?`, `fecha_postulacion`.

Proceso: `estado` (enum, indexado), `es_finalista` (bool).

Resultados de IA: `score_cv?` (0-100), `match_porcentaje?`, `clasificacion_ia?` (`altamente_recomendado` / `recomendado` / `requiere_revision` / `no_apto`), `resumen_ia?`, `habilidades_detectadas` (JSON), `inconsistencias` (JSON), `analizado_en?`.

| Campo | Tipo | Notas |
|---|---|---|
| score_final | float? | **DEC-007:** `(score_cv/5) × 0.20 + nota_examen × 0.40 + nota_entrevista × 0.40`, redondeado a 2 decimales; nulo mientras falte una nota. Es una recomendación para el ranking |
| en_banco_talento | bool | **Planificado (DEV-A-08 · HU-14).** Default false. Marca al candidato como disponible para procesos futuros |

#### Máquina de estados (DEC-009)

Implementado (DEV-C-10 · PR #13): `postulado`, `cv_analizando`, `cv_por_confirmar`, `cv_aprobado`, `cv_rechazado`, `examen_pendiente`, `examen_rendido`, `examen_por_confirmar`, `examen_aprobado`, `examen_rechazado`, `entrevista_pendiente`, `entrevista_realizada`, `finalista`, `contratado`, `descartado`. Los estados de avance y descarte solo se alcanzan con una decisión humana registrada; una prueba automática lo verifica (TST-C-04 · PR #14).

Un CV escaneado (sin texto extraíble) no pasa por la IA: queda en `cv_por_confirmar` con clasificación `requiere_revision` para revisión manual (DEV-A-05).

| Estado | Cómo se llega |
|---|---|
| `postulado` → `cv_analizando` → `cv_por_confirmar` | Automático |
| `cv_aprobado` (token y correo de examen) / `cv_rechazado` (correo de cierre) | **Decisión humana** |
| `examen_pendiente` → `examen_rendido` → `examen_por_confirmar` | Automático |
| `examen_aprobado` (token e invitación) / `examen_rechazado` (correo de cierre) | **Decisión humana** |
| `entrevista_pendiente` → `entrevista_realizada` | Automático |
| `finalista` (correo de finalista) / `descartado` (correo de cierre) | **Decisión humana** |
| `contratado` | Decisión humana, registro manual |

`cambiar-estado` no puede asignar ningún estado de decisión humana.

### Tag — `tags` — Implementado

`id`, `tenant_id`, `nombre` (str(50)), `color?` (str(20), hexadecimal).

### CandidatoTag — `candidato_tags` — Implementado (DEV-C-05 · PR #12)

| Campo | Tipo | Notas |
|---|---|---|
| candidato_id | str | FK; parte de la PK |
| tag_id | str | FK; parte de la PK |
| tenant_id | str(36) | Para la política de RLS |

Las dos FK son `ON DELETE CASCADE`: borrar una etiqueta o un candidato borra sus asignaciones. Índice por `tag_id` para el filtro del listado.

### NotaCandidato — `notas_candidato` — Implementado

| Campo | Tipo | Notas |
|---|---|---|
| id | str (UUID) | PK |
| tenant_id | str(36) | |
| candidato_id | str | FK, indexado |
| autor_id | str | FK a `usuarios`, indexado |
| contenido | str | |
| created_at | datetime | |
| updated_at | datetime? | **Implementado (DEV-A-01 · PR #17).** Fecha de la última edición; nulo si nunca se editó |

Solo el autor edita su nota; el autor o un admin la eliminan. Nunca visibles para el candidato.

### DecisionCandidato — `decisiones_candidato` — Implementado (DEV-C-10 · PR #13, DEC-009)

Registro de **solo inserción**. Fuente del indicador del OE3 (consulta en `docs/metricas/oe3_registro_decisiones.sql`, TST-C-04).

| Campo | Tipo | Notas |
|---|---|---|
| id | str (UUID) | PK |
| tenant_id | str(36) | |
| candidato_id | str | FK, indexado |
| etapa | enum | `cv` / `examen` / `entrevista` |
| recomendacion_ia | enum? | `avanzar` / `descartar`; nulo en la entrevista si no hay umbral |
| puntaje, umbral | float? | Puntaje de la etapa y criterio aplicado |
| justificacion_ia | str? | |
| decision | enum | `avanzar` / `descartar` |
| coincide_con_ia | bool? | |
| justificacion_humana | str? | **Obligatoria** si `coincide_con_ia` es false |
| decidido_por | str | FK a `usuarios` |
| revision_inicio | datetime? | Para medir minutos de evaluación (OE1) |
| decidido_en | datetime | |
| reemplaza_a | str? | FK a `decisiones_candidato` |

## models/evaluacion.py — Implementado

**Examen — `examenes`:** `id`, `tenant_id`, `candidato_id`, `vacante_id`, `estado` (`generando` / `pendiente` / `en_curso` / `finalizado` / `expirado`), `nota?` (0-20), `duracion_minutos` (default 45), `semaforo` (`verde` / `amarillo` / `rojo`), `puntaje_riesgo` (default 0), `fecha_inicio?`, `fecha_fin?`, `created_at`.

**PreguntaExamen — `preguntas_examen`:** `id`, `tenant_id`, `examen_id`, `orden` (1-10), `tipo` (`multiple_choice` / `abierta`), `enunciado`, `opciones_json?`, `respuesta_correcta?`, `respuesta_candidato?`, `puntos_max` (2.0), `puntos_obtenidos?`, `feedback_ia?`. Distribución: 6 de opción múltiple + 4 abiertas = 20 puntos.

**EventoAuditoria — `eventos_auditoria`:** `id`, `tenant_id`, `examen_id?`, `entrevista_id?` (exactamente uno), `tipo` (str(50), catálogo en el doc 07), `severidad` (`baja` / `media` / `alta`), `detalle?`, `timestamp`.

## models/entrevista.py — Implementado

**EntrevistaIA — `entrevistas_ia`:** `id`, `tenant_id`, `candidato_id`, `vacante_id`, `plantilla_id?`, `estado` (`pendiente` / `en_curso` / `finalizada` / `expirada`), `nota?`, `transcripcion?`, `audio_url?`, `duracion_minutos?`, `dimensiones_json?`, `fecha_inicio?`, `fecha_fin?`, `created_at`.

**PlantillaEvaluacion — `plantillas_evaluacion`:** `id`, `tenant_id`, `nombre`, `descripcion?`, `activa`, `created_at`.

**DimensionEvaluacion — `dimensiones_evaluacion`:** `id`, `tenant_id`, `plantilla_id`, `nombre`, `descripcion?`, `peso` (la suma por plantilla debe ser 100), `puntaje_maximo` (20.0).

Plantillas predefinidas: Técnico Estándar (Claridad 20%, Coherencia 20%, Precisión técnica 30%, Comunicación 20%, Seguridad 10%), Comercial (Persuasión 30%, Escucha activa 20%, Orientación a resultados 25%, Manejo de objeciones 25%), Liderazgo (Visión 25%, Gestión de equipos 25%, Decisiones 25%, Comunicación ejecutiva 25%), Creativo (Originalidad 30%, Pensamiento divergente 25%, Argumentación 25%, Adaptabilidad 20%). Ninguna dimensión infiere emociones (DEC-001).

**CapturaAuditoria — `capturas_auditoria`:** `id`, `tenant_id`, `entrevista_id`, `tipo` (`identidad` / `periodica` / `sospechosa`), `imagen_url`, `timestamp`. Solo presencia y segunda persona, con consentimiento previo (DEC-002). La captura previa al examen se especifica en el ciclo siguiente (PLN-B-02).

## Relaciones principales

```
Empresa 1—N Usuario · Usuario 1—N Sesion
Empresa 1—N Area · Area 1—N Vacante · Vacante 1—N Candidato
Candidato 1—N TokenAcceso · Candidato 1—N DecisionCandidato
Candidato 1—1 Examen · Examen 1—N PreguntaExamen · Examen 1—N EventoAuditoria
Candidato 1—1 EntrevistaIA · EntrevistaIA 1—N EventoAuditoria · EntrevistaIA 1—N CapturaAuditoria
EntrevistaIA N—1 PlantillaEvaluacion · PlantillaEvaluacion 1—N DimensionEvaluacion
Candidato N—N Tag (candidato_tags) · Candidato 1—N NotaCandidato
```

Total: 18 tablas implementadas (las 15 iniciales más `sesiones`, `candidato_tags` y `decisiones_candidato`). Queda planificado un campo: `Candidato.en_banco_talento`.

## Aislamiento en la base de datos (DEC-010, DEC-014, DEC-018, DEC-021) — Implementado (DEV-C-11 · PR #10)

```sql
ALTER TABLE <tabla> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <tabla> FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_tenant ON <tabla>
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
```

| Rol | Uso |
|---|---|
| `vael_owner` | Dueño de las tablas; migraciones |
| `vael_app` | Peticiones normales; sin superusuario ni `BYPASSRLS` |
| `vael_system` | Solo la lista cerrada: login, postulación pública por código, listado público de vacantes, feed XML (DEC-014) y resolución del código del candidato (DEC-021) |

El `tenant_id` se fija al inicio de cada transacción (evento `after_begin`). **Las Lambdas no acceden a la base de datos** (DEC-018): entregan sus resultados al backend, que persiste con `vael_app` y el tenant del mensaje.

Toda tabla nueva con datos de una empresa incluye `tenant_id` y su política de RLS en la misma migración que la crea.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1 | 2026-09-15 | Versión inicial |
| 2.0 | 2026-10-13 | Alineado con el código real; estados y decisiones (DEC-009); score (DEC-007); RLS (DEC-010); sesiones (DEC-011) |
| 2.1 | 2026-10-18 | Campos planificados de la retrospectiva: `Vacante.textos_publicacion`, `Candidato.en_banco_talento`, `NotaCandidato.updated_at`; reglas de eliminación de áreas y vacantes; alta de empresa por script (DEC-015); lista cerrada con el feed XML (DEC-014); Lambdas sin acceso a la base de datos (DEC-018); referencias a historias de usuario |
| 2.2 | 2026-10-27 | Cierre del Sprint 1: pasan a implementados `sesiones`, `candidato_tags`, `decisiones_candidato`, los estados `*_por_confirmar`, `token_version`, `textos_publicacion`, `NotaCandidato.updated_at` y la RLS. Campo nuevo `Empresa.email_contacto`. Reglas de áreas (código único) y vacantes (sin candidatos, `cerrada` final). DEC-021 en la lista cerrada |
