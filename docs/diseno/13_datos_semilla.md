> COPIA del documento del Drive `VAEL/Docs/13_datos_semilla.md`, versión 1.3 — **APROBADO** (2026-10-18); ampliación aprobada por el Product Owner el 2026-10-28, copiada el 2026-10-28.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 13 — Datos semilla

| Campo | Valor |
|---|---|
| Versión | 1.3 — **APROBADO** (2026-10-18); ampliación aprobada por el Product Owner el 2026-10-28 |
| Tarea de origen | PLN-C-05 |
| Implementación | **Implementado** en HU-21, tarea DEV-C-03 (PR #15): `python -m app.scripts.semillas` (idempotente) y `python -m app.scripts.generar_cvs` |
| Usado por | TST-C-01 (OE4), TST-A-04 (OE1), TST-A-05 (OE2), TST-A-03 (pruebas de extremo a extremo), demo de E3 |

## Reglas

1. **Ningún dato personal real.** Nombres, empresas, teléfonos y trayectorias son ficticios. Los correos usan el dominio reservado `example.com` (RFC 2606), que no puede recibir correo real.
2. **Ninguna contraseña en el repositorio.** El script lee las contraseñas de los usuarios semilla desde variables de entorno: `SEED_PASSWORD_<ROL>` (por ejemplo, `SEED_PASSWORD_ADMIN`) o, si no existe, `SEED_PASSWORD` para todos. Si falta la contraseña de algún rol, el script se detiene con un error que indica la variable que falta; como es idempotente, basta con definirla y volver a ejecutarlo.
3. **Idempotente.** Ejecutar el script dos veces no duplica registros: busca por claves naturales (`codigo` de vacante, `email` de usuario, `codigo_corto` de área).
4. **Cada dato tiene un propósito de prueba.**
5. **Las empresas se crean con el script de alta** (`app.scripts.crear_empresa`, DEC-015); el script de semillas lo reutiliza.

## Empresas (aprobadas)

| Empresa | Uso |
|---|---|
| **Empresa A — Andina Servicios S.A.C.** (ficticia) | Empresa principal: pruebas funcionales, métricas y demo |
| **Empresa B — Pacífico Logística S.A.C.** (ficticia) | Empresa testigo para TST-C-01: tiene datos propios que la empresa A nunca debe ver ni modificar |

Antes de usarlos en una presentación pública, conviene verificar en SUNAT que no coinciden con una razón social real (**pendiente**, P-02 del Sprint 1).

## Usuarios

Empresa A (un usuario por rol, para la matriz de permisos de TST-A-02):

| Rol | Correo |
|---|---|
| admin | `admin@andina.example.com` |
| reclutador | `reclutador@andina.example.com` |
| evaluador | `evaluador@andina.example.com` |
| gerente | `gerente@andina.example.com` |
| reclutador **inactivo** | `inactivo@andina.example.com` (prueba de RF-A-01: login rechazado con 403) |

Empresa B: `admin@pacifico.example.com` y `reclutador@pacifico.example.com`.

Los dos administradores los crea el script de alta (`crear_empresa`); el resto, el script de semillas.

## Áreas

| Empresa | Nombre | Código | Instrucción de IA |
|---|---|---|---|
| A | Tecnología | TI | Valorar la profundidad técnica demostrable y los proyectos verificables |
| A | Comercial | VEN | Valorar la experiencia en ventas, el logro de metas y la comunicación |
| A | Operaciones | OPE | Valorar la experiencia en procesos, logística y mejora continua |
| B | Logística | LOG | — |

## Plantillas de evaluación (empresa A)

Las cuatro plantillas predefinidas del doc 05: Técnico Estándar, Comercial, Liderazgo y Creativo. En los tests se agrega una plantilla **inválida a propósito** (pesos que suman 90) para probar la validación.

## Vacantes

| Código | Empresa | Título | Nivel | Estado | Propósito |
|---|---|---|---|---|---|
| TI-2026-001 | A | Desarrollador Backend Python | semi_senior | abierta | Flujo principal, OE1, OE2, demo |
| VEN-2026-001 | A | Ejecutivo Comercial | junior | abierta | Segundo perfil de evaluación |
| OPE-2026-001 | A | Analista de Operaciones | junior | borrador | Estados de vacante y eliminación en borrador |
| TI-2026-002 | A | Desarrollador Frontend (confidencial) | junior | abierta, confidencial | No debe aparecer en el listado público ni en el feed XML |
| LOG-2026-001 | B | Coordinador Logístico | semi_senior | abierta | Datos de la empresa testigo |

**Plantilla por vacante — DECISIÓN del Product Owner (2026-10-28):** se quita la referencia. `Vacante` no tiene `plantilla_id`: la plantilla pertenece a la empresa y se asocia a la entrevista (doc 05). La columna "Plantilla" de versiones anteriores se retiró.

## Currículums ficticios (20, empresa A)

Se generan como PDF en `backend/seeds/cvs/` **con un script a partir de plantillas de texto**, para que sean reproducibles (confirmado en DEV-C-03). Los 18 textos están en `backend/seeds/cvs_texto/`; CV-TI-11 (escaneado, sin texto extraíble) y CV-TI-12 (dañado) se generan sin texto fuente. Los PDF no se suben al repositorio (`.gitignore`): se regeneran con `python -m app.scripts.generar_cvs`. Los CV de la empresa A no se cargan como candidatos: se registran por la aplicación durante las pruebas y las mediciones. La excepción son los candidatos con el proceso completo de la sección siguiente, que no se usan para medir OE1 ni OE2.

### TI-2026-001 — Desarrollador Backend Python (12 CVs)

| ID | Perfil | Resultado esperado | Propósito |
|---|---|---|---|
| CV-TI-01 | 5 años con Python, FastAPI y PostgreSQL | Score alto → avanzar | Positivo claro; **referencia OE2** |
| CV-TI-02 | 4 años con Django y MySQL | Score alto | Tecnología relacionada |
| CV-TI-03 | 3 años con Python y proyectos en GitHub | Medio-alto | Evidencia verificable |
| CV-TI-04 | 2 años con Java y algo de Python | Cercano al umbral (≈60) | **Caso límite; referencia OE2** |
| CV-TI-05 | Recién egresado con prácticas en Python | Cercano al umbral | Límite por experiencia |
| CV-TI-06 | 6 años con PHP, sin Python | Bajo → descartar | Experiencia sin match |
| CV-TI-07 | Diseñador gráfico sin experiencia técnica | Muy bajo | Negativo claro; **referencia OE2** |
| CV-TI-08 | 5 años con Python, con un vacío de 14 meses | Alto con inconsistencia | Detección de inconsistencias |
| CV-TI-09 | Fechas laborales superpuestas | Inconsistencias detectadas | Coherencia del CV |
| CV-TI-10 | Líder técnico, 12 años | Alto | Sobrecalificación |
| CV-TI-11 | PDF escaneado como imagen | Revisión manual | Ruta de error de extracción |
| CV-TI-12 | PDF dañado | Error controlado | Reporte de fallidos (RF-A-09) |

### VEN-2026-001 — Ejecutivo Comercial (8 CVs)

| ID | Perfil | Propósito |
|---|---|---|
| CV-VEN-01 a CV-VEN-03 | Experiencia comercial con metas cumplidas | Positivos |
| CV-VEN-04 y CV-VEN-05 | Atención al cliente, sin ventas | Casos límite |
| CV-VEN-06 | Desarrollador de software | Negativo frente a la instrucción del área |
| CV-VEN-07 | Sin experiencia laboral | Negativo |
| CV-VEN-08 | Perfil comercial con LinkedIn y portafolio | Extracción de enlaces |

## Candidatos con el proceso completo (empresa A) — Planificado (DEV-A-07 · HU-19)

**Aprobado por el Product Owner el 2026-10-28.** El examen y la entrevista del candidato se construyen en el ciclo siguiente (perfil Candidato), así que sin estos datos el ranking (RF-A-14), los finalistas (RF-A-15, DEC-022) y la revisión de evaluaciones (RF-A-16) se verían vacíos en E3.

| Candidatos (TI-2026-001) | Estado | Datos | Propósito |
|---|---|---|---|
| 3 o 4 | `entrevista_realizada` | Análisis de CV, examen calificado con eventos de proctoring (semáforos distintos), entrevista con transcripción y puntaje por dimensiones, notas | Ranking con `score_final` (DEC-007), lote de finalistas, auditoría |
| 1 | Examen rendido, sin entrevista | `score_final` nulo | Proceso incompleto aparte en el ranking (RF-A-14) |

Reglas: datos ficticios como el resto del documento; sin datos de emociones (DEC-001); las decisiones de avance se registran en `decisiones_candidato` como en un proceso real (DEC-009). El detalle de cada candidato se fija al implementarlo en DEV-A-07 y se agrega a este documento.

## Uso en AWS

Cada encendido del entorno temporal crea la base desde cero y ejecuta el script de semillas (doc 09). Los usuarios semilla usan la misma `SEED_PASSWORD` que el entorno local; lo que se registre en AWS se pierde al apagar.

## Muestras para las métricas (aprobadas)

| Métrica | Muestra |
|---|---|
| OE1 (etapa de CV) | CV-TI-01 a CV-TI-10 (sin los PDF con fallas) |
| OE2 | CV-TI-01, CV-TI-04 y CV-TI-07, 10 ejecuciones cada uno (30 llamadas a Gemini) |

## Datos de la empresa B

Un área, una vacante, 3 candidatos con su análisis, un examen y una nota interna: cubren cada tipo de recurso al que un endpoint de la empresa A podría intentar acceder en TST-C-01. **Implementado** tal cual en el script de semillas.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-14 | Borrador |
| 1.1 | 2026-10-18 | Aprobado: nombres de las empresas, muestras de OE1 y OE2; alta de empresas con el script de DEC-015; vacante en borrador usada también para la eliminación |
| 1.2 | 2026-10-27 | Estado de implementación (DEV-C-03 · PR #15): scripts, variables `SEED_PASSWORD`, generación de los PDF confirmada; columna de plantilla sin campo en el modelo (pendiente de decisión); verificación en SUNAT pendiente |
| 1.3 | 2026-10-28 | Decisiones del Product Owner: se retira la columna "Plantilla" (sin `plantilla_id` en la vacante) y se aprueban candidatos con el proceso completo para E3 (planificado en DEV-A-07); uso de las semillas en AWS |
