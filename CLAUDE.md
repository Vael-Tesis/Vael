# CLAUDE.md — VAEL

Instrucciones para Claude Code en este repositorio. Este archivo **se deriva** de la documentación del proyecto (Drive `VAEL/Docs`, la fuente de verdad) y de los ADRs de `docs/decisiones/`. Para el detalle de diseño, lee las copias en `docs/diseno/` (DEC-019): **no las edites**; si encuentras una contradicción, detente y avisa. Si este archivo contradice a un ADR, manda el ADR. Versión 2.2 — 2026-10-18.

## 1. Qué es VAEL

Plataforma SaaS multiempresa de apoyo a la preselección de personal para empresas peruanas, con IA bajo supervisión humana. Dos perfiles: **Admin RRHH** (ruta A, este ciclo) y **Candidato** (ruta B, siguiente ciclo). El proceso tiene 19 etapas (`docs/diseno/07_flujo_proceso.md`): postulación → análisis de CV → examen técnico → entrevista por voz con EVA (Gemini Live) → puntaje final → ranking.

**Principio rector: la IA recomienda; RRHH decide.**

## 2. Antes de cualquier tarea

1. La tarea viene del Sprint Backlog del sprint en curso (roadmap `11_roadmap_post_E2.md` y Product Backlog). Una sesión = una tarea. Pide su ID y su criterio de aceptación (CA) si no los tienes.
2. Lee los ADRs de `docs/decisiones/` y los documentos de `docs/diseno/` que afecten a la tarea (servicios: `08_servicios_negocio.md`; vistas: `15_matriz_admin_y_endpoints.md`; requerimientos: `16_requerimientos_admin.md`; datos de prueba: `13_datos_semilla.md`).
3. Trabaja en `feature/<ID>` creada desde `develop`. **Nunca** commitees en `main` ni en `develop`.
4. **Detente y pregunta** si la tarea exige un endpoint o campo no documentado, contradice un ADR, requiere credenciales o genera costos en AWS, o si el CA es ambiguo.
5. No modifiques `deploy.yml` ni recursos de AWS fuera de la etapa de Despliegue.

## 3. Reglas de dominio — OBLIGATORIAS

| # | Regla | Fuente |
|---|---|---|
| 1 | **Ningún servicio de IA decide.** Los análisis dejan al candidato en `cv_por_confirmar` / `examen_por_confirmar` con una recomendación. Solo el servicio de decisiones cambia a estados de avance o descarte, emite tokens y envía correos al candidato, y siempre registra la fila en `decisiones_candidato` | DEC-009 |
| 2 | `decisiones_candidato` es de **solo inserción**. Revertir = insertar una decisión nueva con `reemplaza_a` | DEC-009 |
| 3 | Una decisión contraria a la recomendación exige `justificacion_humana` (422 si falta). El lote solo acepta decisiones que coinciden con la IA | DEC-009 |
| 4 | **Prohibido** inferir emociones: nada de emociones faciales ni análisis de sentimiento. Rekognition solo para presencia y segunda persona, con consentimiento previo | DEC-001, DEC-002 |
| 5 | `score_final = (score_cv/5)*0.20 + nota_examen*0.40 + nota_entrevista*0.40`, redondeado a 2 decimales; `null` si falta alguna nota. Pesos como constantes con nombre | DEC-007 |
| 6 | Al descarte confirmado se envía un único correo de cierre, sin puntajes ni razones. A un descartado nunca se le envía un correo de avance | DEC-013 |

## 4. Reglas multiempresa — OBLIGATORIAS

| # | Regla | Fuente |
|---|---|---|
| 1 | Toda tabla con datos de una empresa tiene `tenant_id` y su política de RLS **en la misma migración** que la crea | DEC-010 |
| 2 | Toda consulta filtra por `tenant_id` en la aplicación, aunque exista RLS | DEC-010 |
| 3 | El backend se conecta como `vael_app`; las migraciones, como `vael_owner`. **Nunca como superusuario** (ignora la RLS) | DEC-010 |
| 4 | La sesión del sistema (`vael_system`, con `BYPASSRLS`) solo se usa en la lista cerrada: login, postulación pública por código, listado público de vacantes, feed XML y resolución del código del candidato. Ampliarla requiere un ADR | DEC-010, DEC-014, DEC-021 |
| 5 | Las tareas asíncronas se publican con `despachar_tarea(tipo, payload)`, nunca llamando a SQS o a `BackgroundTasks` directamente. Cada mensaje lleva el `tenant_id` | DEC-016 |
| 6 | **Las Lambdas no acceden a la base de datos.** Procesan con Gemini y entregan el resultado al backend por `/api/interno/...`, firmado con HMAC-SHA256 y marca de tiempo (máximo 5 minutos). El backend fija el tenant, persiste con RLS y verifica la idempotencia | DEC-018 |
| 7 | El alta de una empresa se hace con `python -m app.scripts.crear_empresa`, nunca con un endpoint | DEC-015 |

## 5. Stack

- **Backend:** Python 3.12, FastAPI, SQLModel, Alembic, asyncpg, PostgreSQL 16. Gunicorn + UvicornWorker en producción.
- **IA:** Gemini (texto) y Gemini Live (voz) con **`google-genai`**. `google-generativeai` está deprecado y se elimina (DEV-C-04).
- **Auth:** JWT propio HS256 con **PyJWT** (reemplaza a `python-jose`, DEC-011). Access token de 15 min; refresh tokens con rotación en la tabla `sesiones`; `token_version` en `Usuario`. Sin Cognito.
- **Sin Redis ni ElastiCache** (DEC-012).
- **Frontend:** React 19 + Vite 8 + Tailwind 4 + TanStack Query + React Router 7, en migración a **TypeScript estricto** (DEC-008).
- **AWS (DEC-016 y DEC-018):** CloudFront como entrada única (`/*` → S3 con el frontend; `/api/*` → ALB), ECS Fargate en subred pública sin entrada directa, RDS PostgreSQL en subred privada (una zona), SQS + Lambda (fuera de la VPC) para tareas asíncronas, SES, Secrets Manager, CloudWatch. **Sin NAT Gateway, sin Cognito, sin ElastiCache.** Dominio: `vael.work` (por configurar).

## 6. Reglas del frontend (DEC-008)

- Una pantalla migrada es `.tsx`, usa solo el cliente tipado (`src/api/cliente.ts`, generado desde `/openapi.json`), no tiene `any` explícito sin justificar y no usa mocks.
- Los datos simulados (`devFallback`) solo se activan con `VITE_MOCKS=true`, desactivado por defecto.
- Si el frontend necesita una ruta o un campo que no existe en el OpenAPI, **no lo inventes**: se agrega primero en el backend y en el doc 06 del Drive (y su copia en `docs/diseno/`).
- Colores solo mediante las variables CSS de la paleta de VAEL; el Figma prevalece sobre la landing.

## 7. Metodología (DEC-017)

Enfoque iterativo e incremental basado en Scrum, con sprints de 1 semana. Product Owner: Gabriel Llanos. Scrum Master: Diego Nina.

**Definition of Done** de cada historia: (1) PR revisado e integrado a `develop`; (2) CI en verde; (3) criterio de aceptación verificado; (4) pruebas de la historia en verde; (5) documentos actualizados si cambió el contrato o el modelo; (6) desplegada en AWS una vez que el entorno existe.

## 8. Estructura

```
backend/app/
  core/       config, database (RLS), dependencies, despacho, gemini, logs, proctoring,
              scoring, security
  models/     un archivo por dominio (`docs/diseno/05_modelos_bd.md`)
  routers/    auth, areas, plantillas, vacantes, candidatos, evaluaciones, entrevista, publico
  schemas/
  scripts/    crear_roles (DEC-010), crear_empresa (DEC-015), semillas y generar_cvs (doc 13),
              exportar_openapi (DEC-008)
  services/   analisis_cv, examen, entrevista_ia, decisiones (DEC-009), correos, vacante_ia,
              aws_services
  templates/emails/
backend/alembic/versions/
backend/seeds/cvs_texto/   textos de los CV ficticios (los PDF se generan)
backend/tests/
frontend/src/
docs/decisiones/   ADRs
docs/diseno/       copias de los docs de diseño del Drive (no editar)
scripts/           sincronizar-diseno.ps1
```

## 9. Estados del candidato (`docs/diseno/05_modelos_bd.md`)

`postulado` → `cv_analizando` → `cv_por_confirmar` → **decisión** → `cv_aprobado` | `cv_rechazado`
`examen_pendiente` → `examen_rendido` → `examen_por_confirmar` → **decisión** → `examen_aprobado` | `examen_rechazado`
`entrevista_pendiente` → `entrevista_realizada` → **decisión** → `finalista` | `descartado`

`cambiar-estado` nunca asigna un estado que requiera decisión humana.

## 10. API

El contrato detallado es el OpenAPI de FastAPI (`/openapi.json`). `docs/diseno/06_api_endpoints.md` lista las rutas, los permisos y los cambios planificados. Niveles de permiso: público, candidato, autenticado, reclutador+ (`admin`, `gerente`, `reclutador`), admin o gerente, admin.

## 11. Proctoring (`docs/diseno/07_flujo_proceso.md`)

Examen: `perdida_foco` 3, `cambio_ventana` 4, `pantalla_dividida` 3, `inactividad` 2, `copy_paste` 6, `click_derecho` 5, `devtools` 8.
Entrevista: `multiples_voces` 10, `sin_rostro` 8, `segunda_persona` 10.
Semáforo: verde ≤ 6, amarillo 7–18, rojo ≥ 19. Es informativo: nunca descalifica.

## 12. Calidad antes de cada commit

```bash
# backend
cd backend
ruff check .          # todo el backend, incluida alembic/
pytest -v

# contrato tipado (DEC-008): si cambió una ruta o un schema del backend
cd backend && python -m app.scripts.exportar_openapi
cd frontend && npm run api:generar      # commitea openapi.json y src/api/esquema.d.ts

# frontend
cd frontend
npx tsc --noEmit
npx vite build
```

El CI ejecuta lo mismo y bloquea el merge si falla.

## 13. Commits y ramas

- Commits convencionales con el ID de la tarea: `feat(DEV-A-04): ...`, `fix(DEV-C-01): ...`, `docs(PLN-C-02): ...`, `test(TST-C-01): ...`, `chore(PLN-C-04): ...`.
- `feature/<ID>` → PR a `develop` → CI en verde → revisión del otro integrante → merge.
- Al terminar: muestra el diff, la salida de lint y tests, y el mensaje de commit propuesto. **No mergees.**

## 14. Variables de entorno

Ver `backend/.env.example`; el detalle de infraestructura está en el doc 09 del Drive. Nunca guardes valores reales de secretos en el repositorio. En producción, `DEBUG=false` (deshabilita `/docs`).

## 15. Desarrollo local

```bash
docker-compose up -d db
cd backend && pip install -r requirements.txt -r requirements-dev.txt
python -m app.scripts.crear_roles   # crea vael_owner, vael_app y vael_system (DEC-010)
alembic upgrade head                # migra como vael_owner
python -m app.scripts.semillas       # datos del doc 13; requiere SEED_PASSWORD en el entorno
uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev
```

## 16. Contexto académico

Proyecto de Fin de Carrera, Tecsup 2026-2 (línea StartUp). Equipo: Gabriel Llanos y Diego Nina. Asesor: Jaime Farfán. El historial de commits es un anexo de la tesis: cada commit debe poder explicarse por quien lo integró.
