# VAEL — Contexto completo para Claude Code

> Lee este archivo completo antes de escribir cualquier línea de código.
> Es la fuente de verdad de todas las decisiones técnicas, de negocio y de implementación.
> Si algo no está aquí, pregunta antes de inventar.

---

## 1. ¿Qué es VAEL?

VAEL (numerónimo de "evaluate" → eval → vael, misma filosofía que n8n) es una plataforma SaaS global de reclutamiento con Inteligencia Artificial. Automatiza el proceso completo de selección de personal en 20 etapas:

- Análisis automático de CVs con Google Gemini (score 0-100)
- Generación y calificación automática de exámenes técnicos
- Entrevista conversacional por voz con EVA (Gemini Live API)
- Análisis emocional facial con AWS Rekognition
- Análisis de sentimiento con AWS Comprehend
- Ranking automático ponderado de candidatos

**Repositorio:** github.com/Vael-Tesis/Vael
**Licencia:** Apache 2.0
**Contexto académico:** Pre-Tesis — Diseño y Desarrollo de Software, Tecsup 2026-2
**Asesor:** Jaime Farfán
**Equipo:** Gabriel Llanos · Diego Nina

---

## 2. Stack tecnológico

```
Backend:      FastAPI 0.115 + SQLModel + Alembic + python-jose
Base datos:   PostgreSQL 16 (asyncpg para async)
IA:           Google Gemini 3 Flash (análisis, exámenes, calificación)
              Google Gemini Live API (entrevista por voz, WebSocket)
AWS IA:       Rekognition (análisis emocional facial — 8 emociones)
              Transcribe (diarización — identifica quién habla)
              Comprehend (sentimiento de la transcripción)
AWS Infra:    ECS Fargate (backend), S3+CloudFront (frontend)
              Lambda (tareas async), Cognito (multi-tenant auth)
              SES (correos), API Gateway WebSocket (Gemini Live)
Frontend:     React 19 + Vite + TanStack Query
CI/CD:        GitHub Actions → ECR → ECS Fargate
```

---

## 3. Estructura del monorepo

```
Vael/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py        ← settings desde .env
│   │   │   ├── database.py      ← engine + session async
│   │   │   ├── security.py      ← JWT + hashing
│   │   │   └── dependencies.py  ← get_db, get_current_user, get_tenant, require_rol
│   │   ├── models/
│   │   │   ├── base.py          ← TenantBase + TimestampMixin
│   │   │   ├── usuario.py       ← Usuario, Empresa, TokenAcceso
│   │   │   ├── area.py          ← Area
│   │   │   ├── vacante.py       ← Vacante
│   │   │   ├── candidato.py     ← Candidato, Tag, NotaCandidato
│   │   │   ├── evaluacion.py    ← Examen, PreguntaExamen, EventoAuditoria
│   │   │   └── entrevista.py    ← EntrevistaIA, PlantillaEvaluacion, DimensionEvaluacion, CapturaAuditoria
│   │   ├── schemas/             ← Pydantic schemas request/response
│   │   ├── routers/             ← endpoints FastAPI
│   │   │   ├── auth.py
│   │   │   ├── vacantes.py
│   │   │   ├── candidatos.py
│   │   │   ├── evaluaciones.py
│   │   │   ├── entrevista.py
│   │   │   └── publico.py       ← sin auth (formulario postulación)
│   │   └── services/            ← lógica de negocio pura
│   │       ├── analisis_cv.py
│   │       ├── correos.py
│   │       ├── entrevista_ia.py
│   │       ├── examen.py
│   │       └── aws_services.py
│   ├── alembic/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    ← React 19 (sin cambios de lógica)
├── infra/
├── docs/
│   └── arquitectura.md
├── .github/workflows/
│   ├── ci.yml
│   └── deploy.yml
├── docker-compose.yml
├── CLAUDE.md                    ← este archivo
└── README.md
```

---

## 4. Reglas de código — OBLIGATORIAS

1. **Todo el código en inglés** — variables, funciones, clases, nombres de archivos
2. **Docstrings en español** — para que el equipo entienda sin traducir
3. **Sin referencias a MENTIS** — ni en comentarios, ni en strings, ni en nombres
4. **Async por defecto** — todos los endpoints y servicios usan `async/await`
5. **Tenant en todo** — ningún query sin filtrar por `tenant_id`
6. **Servicios sin acoplamiento HTTP** — los services no importan nada de FastAPI
7. **Un modelo = un archivo** en `/models/`
8. **Variables de entorno** siempre desde `core/config.py`, nunca `os.getenv()` directo
9. **Nunca `DEBUG=True` en producción** — verificar `settings.ENVIRONMENT`
10. **Type hints en todas las funciones**

---

## 5. Multi-tenancy

Cada empresa cliente es un **tenant**. El aislamiento se implementa así:

- Todos los modelos heredan `TenantBase` que incluye `tenant_id: str`
- Cognito inyecta `tenant_id` como custom claim en cada JWT
- `get_tenant()` dependency extrae el tenant del token en cada request
- **Todos los queries filtran por `tenant_id`** — sin excepción

```python
# Patrón obligatorio en todos los routers
@router.get("/")
async def listar(
    tenant_id: str = Depends(get_tenant),
    db: AsyncSession = Depends(get_db)
):
    statement = select(Vacante).where(Vacante.tenant_id == tenant_id)
    result = await db.exec(statement)
    return result.all()
```

---

## 6. Flujo completo del proceso (20 etapas)

```
RRHH publica vacante
    ↓
1.  Candidato postula vía formulario público /api/publico/postular/{codigo}
2.  Sistema extrae texto del PDF (PyPDF2 + pdfminer)
3.  Lambda async → Gemini 3 Flash analiza CV → score 0-100
4.  Filtro automático: score ≥ score_cv_minimo → avanza
                       score < score_cv_minimo → estado=cv_rechazado (sin notificación)
5.  SES → correo HTML con link al examen (token único 48hrs)
6.  Candidato accede al portal con token precargado desde URL
7.  Rekognition → foto de identidad (validación facial antes del examen)
8.  Gemini genera 10 preguntas según CV + vacante (6 MC + 4 abiertas)
9.  Examen: 45 min timer, auto-guardado cada respuesta, proctoring activo
10. Calificación: MC automático + abiertas con Gemini (0, 1 o 2 pts)
11. Filtro: nota ≥ nota_minima_examen → avanza
            nota < nota_minima_examen → estado=examen_rechazado (sin notificación)
12. SES → correo invitación a entrevista con link
13. Gemini genera pool dinámico 8-12 preguntas con prioridad (crítica/alta/media)
14. Entrevista voz a voz con EVA (Gemini Live, WebSocket, latencia <1s)
15. Trigger a 5 min del final: EVA adelanta preguntas críticas pendientes
16. Rekognition fotos periódicas cada 3 min + Transcribe diarización
17. Comprehend → análisis de sentimiento de la transcripción
18. Gemini → análisis multidimensional post-entrevista (según plantilla RRHH)
19. Score Final = CV×0.25 + Examen×0.40 + Entrevista×0.35
20. Ranking automático + SES correo a finalistas marcados por RRHH
```

---

## 7. Sistema de scoring

```python
# Fórmula ponderada
score_final = (score_cv * 0.25) + (nota_examen * 0.40) + (nota_entrevista * 0.35)

# Umbrales (configurables por vacante)
SCORE_CV_MINIMO_DEFAULT    = 60   # sobre 100
NOTA_EXAMEN_MINIMO_DEFAULT = 13   # sobre 20
# Entrevista no tiene umbral mínimo — contribuye al score final
```

---

## 8. Endpoints por router

### `auth.py` — `/api/auth/`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/login` | No | Login RRHH → access_token + refresh_token |
| POST | `/refresh` | No | Renueva access_token con refresh_token |
| POST | `/logout` | Sí | Invalida token (blacklist en Redis) |
| GET | `/perfil` | Sí | Datos del usuario autenticado |
| POST | `/usuarios/crear` | Admin | Crea usuario, genera contraseña automática, envía por SES |
| GET | `/usuarios` | Admin/Gerente | Lista usuarios del tenant |
| PUT | `/usuarios/{id}/activar` | Admin | Activa usuario |
| PUT | `/usuarios/{id}/desactivar` | Admin | Desactiva usuario |
| PUT | `/usuarios/{id}/cambiar-password` | Admin | Cambia contraseña |
| POST | `/usuarios/{id}/reenviar-credenciales` | Admin | Reenvía contraseña por correo |

### `vacantes.py` — `/api/vacantes/`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/` | Sí | Lista vacantes del tenant con filtros |
| POST | `/` | Reclutador+ | Crea vacante (wizard 4 pasos) |
| GET | `/{id}` | Sí | Detalle de vacante |
| PUT | `/{id}` | Reclutador+ | Edita vacante |
| POST | `/{id}/publicar` | Reclutador+ | Cambia estado a abierta |
| POST | `/{id}/pausar` | Reclutador+ | Pausa vacante |
| POST | `/{id}/cerrar` | Reclutador+ | Cierra vacante |
| POST | `/{id}/duplicar` | Reclutador+ | Crea copia en borrador |
| POST | `/{id}/generar-textos` | Reclutador+ | Gemini genera textos para LinkedIn, WhatsApp, etc. |
| GET | `/{id}/feed-xml` | No | Feed XML para Indeed |

### `candidatos.py` — `/api/candidatos/`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/` | Sí | Lista candidatos con filtros (vacante, estado, clasificación) |
| POST | `/` | Reclutador+ | Registro manual de candidato |
| GET | `/{id}` | Sí | Detalle completo del candidato |
| PUT | `/{id}` | Reclutador+ | Edita candidato |
| POST | `/{id}/analizar` | Reclutador+ | Dispara análisis IA del CV |
| POST | `/{id}/cambiar-estado` | Reclutador+ | Cambia estado manualmente |
| POST | `/{id}/marcar-finalista` | Reclutador+ | Marca como finalista |
| POST | `/{id}/reenviar-correo-etapa` | Reclutador+ | Reenvía correo según etapa actual |
| GET | `/{id}/notas` | Sí | Lista notas internas |
| POST | `/{id}/notas` | Sí | Agrega nota interna |
| GET | `/ranking` | Sí | Ranking por vacante ordenado por score_final |
| POST | `/carga-masiva` | Reclutador+ | Sube múltiples CVs (multipart) |
| GET | `/banco-talento` | Sí | Candidatos con buen score que no quedaron |

### `evaluaciones.py` — `/api/evaluaciones/`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/examenes` | Sí | Lista exámenes del tenant |
| GET | `/examenes/{id}` | Sí | Detalle del examen con preguntas y respuestas |
| GET | `/examenes/{id}/auditoria` | Sí | Eventos de proctoring del examen |
| — | — | — | — |
| POST | `/candidato/acceso` | Token candidato | Valida token y retorna datos del candidato |
| POST | `/candidato/examen/iniciar` | Token candidato | Genera preguntas con Gemini e inicia el examen |
| POST | `/candidato/examen/respuesta` | Token candidato | Guarda respuesta (auto-guardado) |
| POST | `/candidato/examen/finalizar` | Token candidato | Califica examen y notifica a backend |
| POST | `/candidato/examen/evento` | Token candidato | Registra evento de proctoring |
| GET | `/candidato/progreso` | Token candidato | Estado del proceso del candidato |

### `entrevista.py` — `/api/entrevista/`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/acceso` | Token candidato | Valida token para la entrevista |
| POST | `/iniciar` | Token candidato | Genera token efímero Gemini Live + pool de preguntas |
| POST | `/finalizar` | Token candidato | Guarda transcripción, dispara análisis multidimensional |
| POST | `/captura` | Token candidato | Guarda foto de auditoría en S3 |
| POST | `/evento` | Token candidato | Registra evento de auditoría de la entrevista |
| GET | `/detalle/{id}` | Sí | Vista 360° del candidato (nota, dimensiones, audio, transcripción) |

### `publico.py` — `/api/publico/`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/postular/{codigo}` | No | Info de la vacante para el formulario público |
| POST | `/postular/{codigo}/enviar` | No | Recibe postulación + CV (multipart) |
| GET | `/vacantes` | No | Lista vacantes públicas (no confidenciales, estado=abierta) |

---

## 9. Modelos de base de datos

### Campos comunes (heredados de `TenantBase`)
```python
tenant_id: str  # UUID de la empresa — en TODOS los modelos
```

### Usuario
```python
id, tenant_id, nombre, apellidos, email, password_hash,
rol (admin|reclutador|evaluador|gerente), telefono, activo,
created_at, updated_at
```

### Empresa
```python
id, tenant_id (unique), nombre, logo_url, activa, created_at
```

### TokenAcceso
```python
id, tenant_id, candidato_id, token (unique), codigo_corto (VAEL-XXXX-XXXX),
tipo (examen|entrevista), expira_en, usado, created_at
```

### Area
```python
id, tenant_id, nombre, codigo_corto, descripcion, instruccion_ia, activa,
created_at, updated_at
```

### Vacante
```python
id, tenant_id, area_id, codigo (único: TI-2026-001), titulo,
descripcion, responsabilidades, requisitos, requisitos_deseables,
beneficios, habilidades, tecnologias,
nivel_experiencia (practicante|junior|semi_senior|senior|lider),
anios_experiencia, modalidad (presencial|remoto|hibrido),
tipo_contrato (indefinido|plazo_fijo|practicas|freelance|part_time),
ciudad, pais, salario_minimo, salario_maximo, moneda, mostrar_salario,
confidencial, estado (borrador|abierta|pausada|cerrada),
prioridad (baja|media|alta|urgente), fecha_limite,
jefe_directo, solicitante, cantidad_posiciones,
score_cv_minimo (default=60), nota_minima_examen (default=13),
top_candidatos_finalistas (default=5), instruccion_ia_extra,
created_at, updated_at
```

### Candidato
```python
id, tenant_id, vacante_id, nombre, apellidos, email, telefono,
linkedin, github, portfolio, cv_url,
estado (postulado|cv_analizando|cv_aprobado|cv_rechazado|
        examen_pendiente|examen_rendido|examen_aprobado|examen_rechazado|
        entrevista_pendiente|entrevista_realizada|finalista|contratado|descartado),
es_finalista, pretension_salarial,
score_cv, match_porcentaje,
clasificacion_ia (altamente_recomendado|recomendado|requiere_revision|no_apto),
resumen_ia, habilidades_detectadas, inconsistencias, analizado_en,
score_final, fecha_postulacion, created_at, updated_at
```

### Tag
```python
id, tenant_id, nombre, color
```

### NotaCandidato
```python
id, tenant_id, candidato_id, autor_id, contenido, created_at
```

### Examen
```python
id, tenant_id, candidato_id, vacante_id,
estado (generando|pendiente|en_curso|finalizado|expirado),
nota, duracion_minutos,
semaforo (verde|amarillo|rojo), puntaje_riesgo,
fecha_inicio, fecha_fin, created_at
```

### PreguntaExamen
```python
id, tenant_id, examen_id, orden, tipo (multiple_choice|abierta),
enunciado, opciones_json, respuesta_correcta,
respuesta_candidato, puntos_max (default=2.0),
puntos_obtenidos, feedback_ia
```

### EventoAuditoria
```python
id, tenant_id, examen_id, tipo, severidad (baja|media|alta),
detalle, timestamp
```

### EntrevistaIA
```python
id, tenant_id, candidato_id, vacante_id, plantilla_id,
estado (pendiente|en_curso|finalizada|expirada),
nota, transcripcion, audio_url, duracion_minutos,
dimensiones_json, fecha_inicio, fecha_fin, created_at
```

### PlantillaEvaluacion
```python
id, tenant_id, nombre, descripcion, activa, created_at
```

### DimensionEvaluacion
```python
id, tenant_id, plantilla_id, nombre, descripcion,
peso, puntaje_maximo (default=20.0)
```

### CapturaAuditoria
```python
id, tenant_id, entrevista_id,
tipo (identidad|periodica|sospechosa),
imagen_url, timestamp
```

---

## 10. Servicios de negocio

### `analisis_cv.py`
```
Función principal: analizar_cv(cv_url, vacante, area)
1. Descarga PDF desde S3
2. Extrae texto con PyPDF2 + pdfminer como fallback
3. Construye prompt con: texto_cv + requisitos_vacante + instruccion_area
4. Llama a Gemini 3 Flash
5. Parsea respuesta JSON:
   - score: int (0-100)
   - clasificacion: str (altamente_recomendado|recomendado|requiere_revision|no_apto)
   - resumen: str (3-4 oraciones)
   - habilidades_detectadas: list[str]
   - inconsistencias: list[str]
   - linkedin: str | None (extraído del PDF)
   - github: str | None
   - portfolio: str | None
6. Actualiza candidato en BD
7. Si score >= score_cv_minimo: genera token + envía correo examen
8. Si score < score_cv_minimo: cambia estado a cv_rechazado (sin correo)
```

### `examen.py`
```
Función: generar_preguntas(cv_texto, vacante, area)
- Llama a Gemini para generar 10 preguntas
- Distribución: 6 opción múltiple (4 opciones c/u) + 4 abiertas
- Retorna lista de PreguntaExamen

Función: calificar_examen(examen_id)
- MC: compara respuesta_candidato con respuesta_correcta → 0 o 2 pts
- Abiertas: Gemini evalúa respuesta → 0, 1 o 2 pts con feedback
- Calcula nota final (suma / 20)
- Actualiza semáforo según puntaje_riesgo:
  - Verde: puntaje_riesgo <= 6
  - Amarillo: 7-18
  - Rojo: > 18
- Si nota >= nota_minima_examen: envía correo entrevista
- Si nota < nota_minima_examen: estado=examen_rechazado (sin correo)
```

### `entrevista_ia.py`
```
Función: generar_token_efimero_live()
- Llama a Gemini Live API para obtener token efímero
- Token válido 30 min (newSessionExpireTime = 10 min para iniciar)
- Retorna token para que el frontend abra el WebSocket

Función: generar_pool_preguntas(candidato, vacante, plantilla)
- Genera 8-12 preguntas con Gemini
- Cada pregunta tiene: enunciado, prioridad (crítica|alta|media)
- Las críticas se adelantan si quedan < 5 min

Función: analizar_entrevista(transcripcion, dimensiones)
- Llama a Gemini con la transcripción completa
- Evalúa cada dimensión de la plantilla (nota 0-20 por dimensión)
- Calcula nota final ponderada
- Retorna dimensiones_json y nota
```

### `correos.py`
```
Correos que se envían (solo a candidatos que AVANZAN, nunca en rechazos):

1. correo_bienvenida_examen(candidato, token)
   - Asunto: "Tu evaluación técnica está lista — [nombre_vacante]"
   - Incluye: link con token precargado, instrucciones, tiempo límite

2. correo_invitacion_entrevista(candidato, token)
   - Asunto: "¡Felicitaciones! Pasaste al siguiente paso — [nombre_vacante]"
   - Incluye: link a la entrevista, qué es EVA, cómo prepararse

3. correo_finalista(candidato, vacante)
   - Asunto: "Eres finalista en [nombre_vacante]"
   - Incluye: próximos pasos (entrevista presencial o contratación)

4. correo_credenciales_usuario(usuario, password_temporal)
   - Asunto: "Bienvenido a VAEL — Tus credenciales de acceso"
   - Incluye: email, contraseña temporal, link al sistema

Todos los correos:
- Se envían vía AWS SES en producción
- Se envían vía SMTP local en desarrollo
- Usan plantillas HTML con Jinja2
- Nunca se envían a candidatos rechazados (cv_rechazado, examen_rechazado)
```

### `aws_services.py`
```
Rekognition:
  detectar_emociones(imagen_bytes) → dict con 8 emociones y confianza
  validar_identidad(imagen_bytes) → bool (rostro visible y único)

Transcribe:
  transcribir_audio(audio_url) → str con transcripción + diarización

Comprehend:
  analizar_sentimiento(texto) → dict {positivo, negativo, neutral, mixto}

S3:
  subir_archivo(archivo_bytes, key, content_type) → url
  descargar_archivo(key) → bytes
  generar_url_prefirmada(key, expires=3600) → url_temporal

SES:
  enviar_correo(to, subject, html_body, from_email) → bool
```

---

## 11. Proctoring — eventos y severidades

```python
EVENTOS_PROCTORING = {
    # Navegador
    "perdida_foco":      {"severidad": "media",  "puntos": 3},
    "cambio_ventana":    {"severidad": "media",  "puntos": 4},
    "pantalla_dividida": {"severidad": "media",  "puntos": 3},
    "inactividad":       {"severidad": "baja",   "puntos": 2},

    # Entrada
    "copy_paste":        {"severidad": "alta",   "puntos": 6},
    "click_derecho":     {"severidad": "alta",   "puntos": 5},
    "devtools":          {"severidad": "alta",   "puntos": 8},

    # Audio/Video (entrevista)
    "multiples_voces":   {"severidad": "alta",   "puntos": 10},
    "sin_rostro":        {"severidad": "alta",   "puntos": 8},
    "segunda_persona":   {"severidad": "alta",   "puntos": 10},
}

# Semáforo según puntaje_riesgo acumulado
SEMAFORO_VERDE    = (0, 6)    # Sin riesgo
SEMAFORO_AMARILLO = (7, 18)   # Revisión opcional
SEMAFORO_ROJO     = (19, 999) # Revisión obligatoria
```

---

## 12. Variables de entorno

```env
# Entorno
ENVIRONMENT=development
DEBUG=true

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://vael:vael@localhost:5432/vael_db

# JWT
SECRET_KEY=minimo-32-caracteres-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3-flash
GEMINI_LIVE_MODEL=gemini-2.5-flash-native-audio-preview-12-2025

# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET_NAME=vael-storage
SES_REGION=us-east-1

# Correos
EMAIL_FROM=noreply@vael.ai
EMAIL_FROM_NAME=VAEL

# Interno
INTERNAL_SERVICE_KEY=vael-internal-secret-2026

# Frontend
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 13. Cómo levantar el proyecto localmente

```bash
# 1. Clonar
git clone https://github.com/Vael-Tesis/Vael.git
cd Vael

# 2. Levantar PostgreSQL
docker-compose up -d db

# 3. Backend
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # completar con credenciales reales

# 4. Migraciones
alembic upgrade head

# 5. Servidor de desarrollo
uvicorn app.main:app --reload --port 8000
# Docs en: http://localhost:8000/docs

# 6. Frontend (otra terminal)
cd ../frontend
npm install
npm run dev

# O todo junto con Docker
docker-compose up
```

---

## 14. Convención de commits

```
feat: nueva funcionalidad
fix: corrección de bug
refactor: refactorización sin cambio de comportamiento
docs: documentación
test: tests
chore: configuración, dependencias

Ejemplos:
feat: implement auth router with JWT and tenant support
fix: correct score calculation in exam service
feat: add CV analysis with Gemini in background Lambda
```

---

## 15. Contexto académico

- **Pre-Tesis:** Diseño y Desarrollo de Software — Tecsup 2026-2
- **Línea de titulación:** StartUp
- **Semana actual:** 4 de 16
- **E1 (semana 6):** Capítulo 1 monografía + 50% prototipo Figma
- **E2 (semana 9):** Capítulo 2 + 100% Figma + 50% SW programado
- **E3 (semana 11):** Capítulo 3 + 1 perfil programado 100%
- **Sustentación:** Semana 16

El código que escribas es evaluado por el asesor Jaime Farfán (curso: Desarrollo de soluciones en la nube). Debe demostrar dominio de AWS, arquitectura SaaS y buenas prácticas de DevOps.

---

## 16. Origen del código

Este proyecto es la evolución de MENTIS (proyecto integrador Tecsup 2026-I, Grupo 4-A). La lógica de negocio fue migrada y refactorizada completamente — sin referencias a MENTIS en ningún archivo.

Referencia de migración (solo para contexto, nunca mencionar en código):
- `services/analisis_cv.py` ← `candidatos/servicios/analisis_cv.py` (Django → FastAPI)
- `services/correos.py` ← `candidatos/servicios/correos.py`
- `services/entrevista_ia.py` ← `evaluaciones/servicios/entrevista_ia.py`
- `services/examen.py` ← Spring Boot `ExamenService.java` + `GeminiService.java` (Java → Python)
- Todos los modelos son nuevos en SQLModel
- Todos los routers son nuevos en FastAPI
