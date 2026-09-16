# VAEL — Arquitectura del Sistema

**Versión:** 1.0  
**Fecha:** Septiembre 2026  
**Autores:** Gabriel Llanos · Diego Nina  
**Asesor:** Jaime Farfán — Tecsup

---

## Visión general

VAEL es un SaaS multi-tenant de reclutamiento con IA. Un solo backend FastAPI (Python) atiende tanto al panel de RRHH como al portal del candidato, corriendo en AWS ECS Fargate con PostgreSQL en RDS.

---

## Diagrama de arquitectura

```
INTERNET
    │
    ├── CloudFront ──────────────── S3
    │   (CDN global)                (React build compilado)
    │
    ├── API Gateway (WebSocket) ─── ECS Fargate
    │   (Gemini Live entrevista)    (FastAPI — puerto 8000)
    │
    └── ALB (Application Load Balancer)
            │
            └── ECS Fargate — FastAPI
                ├── /api/auth/         ← autenticación RRHH + candidato
                ├── /api/vacantes/     ← gestión de vacantes
                ├── /api/candidatos/   ← gestión + análisis IA
                ├── /api/evaluaciones/ ← examen + proctoring
                ├── /api/entrevista/   ← Gemini Live WebSocket
                └── /api/publico/      ← formulario postulación (sin auth)

DATOS
    ├── RDS PostgreSQL (Multi-AZ)
    │   └── tenant_id en todas las tablas
    ├── S3
    │   ├── CVs subidos por candidatos
    │   ├── Audios de entrevistas
    │   └── Fotos de auditoría
    └── ElastiCache Redis (sesiones + cache análisis CV)

PROCESAMIENTO IA
    ├── Lambda
    │   ├── Análisis CV async (disparado por S3 event)
    │   ├── Procesamiento fotos auditoría
    │   └── Correos masivos vía SES
    ├── AWS Rekognition  → análisis emocional facial (8 emociones)
    ├── AWS Transcribe   → diarización entrevista (quién habla)
    └── AWS Comprehend   → sentimiento de la transcripción

IDENTIDAD MULTI-TENANT
    ├── Cognito User Pool
    │   └── custom claim: tenant_id + rol en cada JWT
    └── FastAPI Dependency
        └── get_tenant() → filtra BD por tenant en cada request

GOOGLE AI
    ├── Gemini 3 Flash   → análisis CV, preguntas examen, calificación
    └── Gemini Live API  → entrevista voz a voz (WebSocket)

MONITOREO
    ├── CloudWatch Logs  → logs de FastAPI + Lambda
    ├── CloudWatch Metrics → CPU, memoria, requests/s, errores
    └── X-Ray            → trazabilidad entre servicios

CI/CD
    ├── GitHub Actions
    │   ├── ci.yml    → tests + lint en cada PR
    │   └── deploy.yml → build Docker → push ECR → update ECS (en merge a main)
    └── ECR (Elastic Container Registry) → imagen Docker del backend
```

---

## Multi-tenancy

### Modelo de aislamiento

Se usa **shared database, shared schema** con Row-Level Security a nivel de aplicación. Es el modelo recomendado por AWS para SaaS con cientos de tenants pequeños/medianos.

Cada tabla tiene:
```sql
tenant_id VARCHAR(36) NOT NULL  -- UUID de la empresa cliente
```

### Flujo de autenticación multi-tenant

```
1. Usuario RRHH hace login → FastAPI valida credenciales
2. FastAPI genera JWT con claims: user_id, tenant_id, rol
3. Cognito firma y distribuye el JWT
4. Cada request incluye JWT en Authorization header
5. FastAPI dependency get_tenant() extrae tenant_id del JWT
6. Todos los queries filtran: WHERE tenant_id = {tenant_id}
```

### Onboarding de nuevo tenant

```
1. Empresa se registra → se crea registro en tabla Empresa
2. Se genera tenant_id único (UUID)
3. Se crea Cognito User Group para esa empresa
4. Se crea usuario admin inicial → se envía correo con credenciales
5. Admin configura áreas, plantillas de evaluación y parámetros de IA
```

---

## Stack tecnológico detallado

### Backend

| Componente | Tecnología | Versión | Razón |
|-----------|-----------|---------|-------|
| Framework | FastAPI | 0.115 | Async nativo, 30k+ req/s, Swagger auto-generado |
| ORM + Validación | SQLModel | 0.0.22 | Un solo modelo = ORM + schema Pydantic |
| Migraciones | Alembic | 1.14 | Estándar con SQLAlchemy/SQLModel |
| Auth JWT | python-jose | 3.3 | Control total sobre claims del token |
| Servidor ASGI | Uvicorn | 0.32 | Recomendado por FastAPI, async nativo |
| Servidor producción | Gunicorn + Uvicorn workers | — | Multi-process en ECS |
| SDK IA | google-generativeai | 0.8 | SDK oficial Python de Gemini (superior al Java) |
| SDK AWS | boto3 | 1.35 | SDK oficial Python de AWS |

### Base de datos

| Componente | Tecnología | Razón |
|-----------|-----------|-------|
| Motor | PostgreSQL 16 | Estándar industria con FastAPI, JSON nativo, full-text search |
| Driver async | asyncpg | Más rápido que psycopg2, nativo async |
| ORM | SQLModel | Reduce boilerplate vs SQLAlchemy puro |
| Cache | Redis (ElastiCache) | Sesiones + cache resultados análisis CV |

### Frontend

React 19 + Vite + TanStack Query. Sin cambios de lógica respecto a MENTIS — solo se actualiza la URL base de la API para apuntar al nuevo backend FastAPI.

---

## Decisiones arquitectónicas documentadas

### DA-01: FastAPI sobre Django
**Decisión:** Migrar de Django REST Framework a FastAPI.
**Razón:** FastAPI es async nativo (30k-40k req/s vs 8k-12k de DRF). Para un sistema de IA con análisis de CV simultáneos y WebSockets de entrevista, el modelo async es crítico. Django WSGI bloquea workers en operaciones I/O pesadas.
**Trade-off aceptado:** Reescritura del backend (~5 días con asistencia IA). La base de código de MENTIS se reutiliza en la capa de servicios de negocio.

### DA-02: Un solo backend Python (eliminación de Spring Boot)
**Decisión:** Eliminar Spring Boot y consolidar toda la lógica en FastAPI.
**Razón:** El SDK de Gemini en Python es el SDK nativo y oficial — tiene soporte completo de Gemini Live, streaming y function calling meses antes que el SDK Java. Mantener dos lenguajes duplica la complejidad DevOps: dos Dockerfiles, dos pipelines, dos estrategias de gestión de secretos.
**Trade-off aceptado:** Reescritura de `ExamenService.java` y `GeminiService.java` en Python (~1 día). La lógica de negocio del examen es directamente portable.

### DA-03: PostgreSQL sobre MySQL
**Decisión:** PostgreSQL en lugar de MySQL (usado en MENTIS).
**Razón:** PostgreSQL es el estándar de la industria con FastAPI/SQLModel. Mejor soporte de tipos JSON nativos, full-text search nativo, y mayor comunidad en ecosistema Python async. AWS RDS PostgreSQL tiene el mismo precio que MySQL.
**Trade-off aceptado:** Los datos de MENTIS no se migran directamente — el sistema arranca limpio.

### DA-04: ECS Fargate sobre Lambda para el backend
**Decisión:** FastAPI corre en ECS Fargate, no en Lambda.
**Razón:** Lambda tiene timeout de 29 segundos (API Gateway) — insuficiente para análisis de CV con Gemini (3-8s bajo carga) y WebSockets de entrevista (15-20 minutos). ECS Fargate mantiene contenedores calientes sin cold starts, con escalado automático.
**Aclaración:** Lambda SÍ se usa para tareas async: procesamiento de CVs en background, fotos de auditoría, correos masivos.

### DA-05: Monorepo
**Decisión:** Un solo repositorio para backend + frontend + infra.
**Razón:** Equipo de 2 personas. Un PR puede cubrir cambios en API y frontend simultáneamente. El pipeline CI/CD coordina deployments y no despliega frontend si el backend falló.

### DA-06: SQLModel sobre SQLAlchemy puro
**Decisión:** SQLModel en lugar de SQLAlchemy directamente.
**Razón:** SQLModel permite definir el modelo una sola vez y usarlo como ORM para la BD y como schema Pydantic para validación/serialización. Reduce el boilerplate a la mitad. Creado por el mismo autor de FastAPI — integración nativa garantizada.

---

## Costo estimado por candidato procesado

| Servicio | Uso | Costo |
|---------|-----|-------|
| Gemini 3 Flash (CV + examen + calificación) | ~30k tokens | ~$0.08–0.12 |
| Gemini Live API (entrevista 20 min) | 20 min audio | ~$0.15 |
| AWS Rekognition (7 fotos) | 7 imágenes | ~$0.007 |
| AWS Transcribe (20 min) | 20 min | ~$0.48 |
| AWS Comprehend (sentimiento) | ~3k chars | ~$0.005 |
| AWS S3 + Lambda + SES | estimado | ~$0.02 |
| **Total por candidato** | | **~$0.74–0.83** |

**Durante desarrollo/tesis:** $0 gracias al AWS Free Tier (12 meses).

---

## Roadmap técnico post-tesis

1. **v1.1** — Migrar auth a Cognito nativo (actualmente JWT propio)
2. **v1.2** — Agregar Elasticsearch para búsqueda de candidatos en banco de talento
3. **v2.0** — Reescribir análisis de CV con fine-tuning de modelo propio sobre datos reales de VAEL
4. **v2.1** — API pública para integraciones con Workday, SAP SuccessFactors
