> COPIA del documento del Drive `VAEL/Docs/14_plan_metricas.md`, versión 1.2 — **APROBADO** (2026-10-18); estado de la instrumentación actualizado el 2026-10-27, copiada el 2026-10-28.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 14 — Plan de métricas

| Campo | Valor |
|---|---|
| Versión | 1.2 — **APROBADO** (2026-10-18); estado de la instrumentación actualizado el 2026-10-27 |
| Tarea de origen | PLN-C-06 |
| Fuente de los objetivos | Monografía, sección 1.2 y Tabla 1.1 |
| Datos de prueba | Doc 13 |
| Destino en la monografía | Capítulo IV (4.1 Entregables) y anexos, según el índice oficial |

## Principio

Cada métrica se define **antes** de implementar, con su fórmula, su fuente y su procedimiento, para que la instrumentación se construya durante los sprints y no se improvise al final. Los datos crudos se conservan para los anexos.

## Métricas de los objetivos específicos

### OE1 — Tiempo de evaluación por candidato

| Aspecto | Definición |
|---|---|
| Meta | Reducción ≥ 50% frente a la evaluación manual |
| Indicador | **Minutos de evaluación humana por candidato** (decisión aprobada en la revisión: R1) |
| Línea base | Evaluación manual cronometrada de los 10 CVs de la muestra con una rúbrica de los 5 criterios del análisis de CV |
| Medición con VAEL | `decidido_en − revision_inicio` en `decisiones_candidato` (DEC-009) |
| Fórmula | `reducción = 1 − (promedio VAEL / promedio manual)` |
| Historia | HU-25, tarea TST-A-04 (etapa de CV, Sprint 2); examen y entrevista en el ciclo siguiente (TST-B-05) |

El tiempo de procesamiento de la IA no consume tiempo del reclutador; se reporta aparte (M-01).

**Amenazas a la validez (se declaran en la monografía):**
- **Aprendizaje de los CVs:** la evaluación manual se hace antes de usar VAEL y **cada integrante evalúa en una sola condición** (aprobado en la revisión: R2).
- **Muestra pequeña y ficticia** (10 CVs), ya declarada como limitación en la sección 1.3.

### OE2 — Consistencia de la calificación automatizada

| Aspecto | Definición |
|---|---|
| Meta | Desviación estándar ≤ 5 puntos sobre 100 |
| Indicador | Desviación estándar del `score_cv` de un mismo CV en 10 ejecuciones |
| Muestra | **CV-TI-01, CV-TI-04 y CV-TI-07** (alto, límite y bajo), 10 ejecuciones cada uno, contra TI-2026-001 (aprobado: R3) |
| Procedimiento | Script que llama al análisis 10 veces por CV sin cambiar la vacante ni el prompt |
| Se registra | ID exacto del modelo, parámetros de generación y fecha de cada ejecución |
| Historia | HU-25, tarea TST-A-05 (Sprint 2) |
| Dependencia | Reintento ante el error 429 de Gemini (HU-21, DEV-C-04) |

Además del puntaje, se reporta si **la recomendación** (avanzar o descartar) cambia entre ejecuciones; para el CV límite es la lectura más relevante.

### OE3 — Registro de las decisiones

| Aspecto | Definición |
|---|---|
| Meta | 100% |
| Fórmula | `candidatos con fila en decisiones_candidato por etapa completada / candidatos que completaron esa etapa` |
| Condición adicional | El 100% de las decisiones contrarias a la IA tiene `justificacion_humana` |
| Verificación continua | TST-C-04 en el CI (historia HU-15) |
| Medición final | Consulta SQL documentada sobre los datos del periodo de validación: `docs/metricas/oe3_registro_decisiones.sql` (cobertura por etapa y decisiones contrarias sin justificación; TST-C-04 · PR #14) |

### OE4 — Despliegue automatizado y aislamiento

| Aspecto | Definición |
|---|---|
| Meta | 0 accesos cruzados; 100% de despliegues automatizados |
| Indicador 1 | Accesos cruzados en la suite TST-C-01 (en dos capas: aplicación y RLS) |
| Cobertura | Endpoints autenticados cubiertos / endpoints autenticados del OpenAPI = 100% (conteo automático) |
| Indicador 2 | Despliegues ejecutados por `deploy.yml` / despliegues totales = 100% |
| Historias | HU-04 (TST-C-01), HU-22 (DEP-C-05) |

## Métricas de apoyo

| ID | Métrica | Fuente | Uso |
|---|---|---|---|
| M-01 | Tiempo de análisis de un CV | `duration_ms` en los logs JSON (DEV-C-08) | Complementa al OE1 |
| M-02 | Tasa de concordancia entre la recomendación de la IA y la decisión de RRHH | `decisiones_candidato.coincide_con_ia` | Evidencia de supervisión efectiva (DEC-009); una tasa cercana al 100% es ambigua y se declara así |
| M-03 | Cambio de recomendación entre ejecuciones del mismo CV | Script de TST-A-05 | Complementa al OE2 |
| M-04 | Métricas DORA: frecuencia de despliegue, tiempo de espera para cambios, tasa de fallos en cambios, tiempo de restauración | Historial de GitHub Actions y de PRs | Propuestas en la sección 2.3.6 de la monografía |
| M-05 | Costo real de AWS | AWS Cost Explorer | Contraste con el doc 02 |
| M-06 | Latencia de EVA | Frontend del candidato | Ciclo siguiente |
| M-07 | Velocidad y cumplimiento del sprint | Burndown y Sprint Board (DEC-017) | Evidencia de la metodología (apartado 3.2) |

## Instrumentación que debe existir

| Requisito | Tarea | Sprint | Estado |
|---|---|---|---|
| `revision_inicio` y `decidido_en` en `decisiones_candidato` | DEV-C-10 | 1 | **Hecho** (PR #13); `revision_inicio` se guarda en UTC y la bandeja lo envía (DEV-A-05) |
| Logs JSON con `operation` y `duration_ms` | DEV-C-08 | 1 | **Hecho** (PR #6) |
| Registro del ID del modelo y los parámetros | DEV-C-04 | 1 | **Hecho** (PR #7) |
| Consulta del indicador OE3 | TST-C-04 | 1 | **Hecho** (PR #14); verificación continua en el CI |
| Conteo automático de endpoints autenticados | TST-C-01 | 2 | Pendiente |
| Script de OE2 | TST-A-05 | 2 | Pendiente |

## Registro de datos crudos

Cada medición guarda sus datos en `docs/metricas/` del repositorio (CSV o JSON) con fecha, SHA del commit y versión del modelo.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-14 | Borrador |
| 1.1 | 2026-10-18 | Aprobado: R1 (minutos-persona), R2 (cada integrante en una condición), R3 (tres CVs para OE2); historias y sprints asociados; métrica M-07 de la metodología; destino en el Capítulo IV según el índice oficial |
| 1.2 | 2026-10-27 | Estado de la instrumentación al cierre del Sprint 1: los cuatro requisitos del Sprint 1 están hechos; consulta del OE3 en `docs/metricas/` |
