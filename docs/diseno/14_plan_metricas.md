> COPIA del documento del Drive `VAEL/Docs/14_plan_metricas.md`, versión 1.7 — **APROBADO** (2026-10-18); estado de la instrumentación y de las mediciones actualizado el 2026-11-10, copiada el 2026-11-10.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 14 — Plan de métricas

| Campo | Valor |
|---|---|
| Versión | 1.7 — **APROBADO** (2026-10-18); estado de la instrumentación y de las mediciones actualizado el 2026-11-10 |
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

**Estado (2026-11-10): sin medir.** Los materiales están integrados en `docs/metricas/oe1/` (TST-A-04 · PR #36): rúbrica con los 5 criterios ponderados, planilla, procedimiento con R2 y consulta SQL de los minutos con VAEL. Los criterios de la rúbrica son los mismos que usa el análisis de VAEL (DEC-024, DEV-C-14 · PR #38). La evaluación manual ya puede hacerse. Falta asignar quién hace cada condición.

### OE2 — Consistencia de la calificación automatizada

| Aspecto | Definición |
|---|---|
| Meta | Desviación estándar ≤ 5 puntos sobre 100 |
| Indicador | Desviación estándar del `score_cv` de un mismo CV en 10 ejecuciones |
| Muestra | **CV-TI-01, CV-TI-04 y CV-TI-07** (alto, límite y bajo), 10 ejecuciones cada uno, contra TI-2026-001 (aprobado: R3) |
| Procedimiento | `python -m app.scripts.medir_oe2 --proveedor gemini\|qwen`: llama al análisis 10 veces por CV sin cambiar la vacante, el prompt, la validación del desglose (DEC-024) ni la regla de recomendación |
| Se registra | Proveedor, ID exacto del modelo (y el servidor, en Qwen), parámetros de generación, fecha y SHA del commit de cada ejecución |
| Historia | HU-25, tareas TST-A-05 y TST-A-06 |
| Dependencia | Reintento ante 429 y 503 (HU-21, DEV-C-04) |

Además del puntaje, se reporta si **la recomendación** (avanzar o descartar) cambia entre ejecuciones (M-03); para el CV límite es la lectura más relevante.

**Dos registros separados (DEC-026, propuesta; TST-A-06 · PR #48):** el OE2 se mide por modelo y cada uno guarda su registro en `docs/metricas/oe2_<proveedor>/`: la corrida completa en `consistencia.json`, los intentos fallidos en `intento_NN_<motivo>.json` y las partes en `partes/`. Ninguno reemplaza al otro y cada cifra se informa con su modelo. Con Gemini se puede medir por partes en días distintos (`--cv` y `--unir`, PR #45) por el límite de 20 solicitudes diarias del plan gratuito.

**Registro de Qwen — medido el 2026-11-10** (`docs/metricas/oe2_qwen/consistencia.json`, commit `dbcc319`): `qwen/qwen3.8-flash` en `openrouter.ai` (proveedor Alibaba), 30 de 30 ejecuciones exitosas.

| CV | Media | Desviación estándar | Meta ≤ 5 | Recomendación |
|---|---|---|---|---|
| CV-TI-01 (alto) | 90,7 | 3,30 | Cumple | `avanzar` en las 10 |
| CV-TI-04 (límite) | 36,6 | 4,22 | Cumple | `descartar` en las 10 |
| CV-TI-07 (bajo) | 2,2 | 3,05 | Cumple | `descartar` en las 10 |

**Observación:** el doc 13 plantea CV-TI-04 cerca del umbral (≈60), pero con este modelo quedó en 36,6. No afecta al OE2, que mide consistencia y no exactitud; queda para revisar con el doc 13.

**Registro de Gemini — sin corrida completa.** Intento del 2026-11-03 (commit `759dd61`, `gemini-3.8-flash`): 30 de 30 ejecuciones fallidas, 24 por la cuota gratuita (429) y 6 por alta demanda (503); se conserva en `docs/metricas/oe2_gemini/intento_01_cuota_agotada.json`. Intento del 2026-11-09: detenido sin resultados por la cuota del día. El 2026-11-10, Gemini respondió 503 en 5 llamadas mínimas entre las 09:09 y las 09:16. La medición con Gemini sigue pendiente.

**Cómo se informa:** «consistencia del análisis de CV con Qwen3.8-Flash, medida el 2026-11-10». El resultado de Qwen no se presenta como medición de Gemini, el modelo del sistema; es una limitación que se declara.

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

**Medición del indicador 1 (TST-C-01 · PR #32, 2026-11-01, commit `a972d83`):** **0 accesos cruzados** en las dos capas. Cobertura del **100%**: 66 de 66 endpoints autenticados de RRHH y 11 de 11 del candidato (DEC-021). Las 5 operaciones de la lista cerrada (6 funciones; DEC-010, DEC-014, DEC-021) quedan fuera del conteo porque usan la sesión del sistema y no llevan `Authorization`. Datos crudos: `docs/metricas/oe4_aislamiento.json`. La suite (`test_aislamiento_multiempresa.py` y `test_rls.py`) corre en cada PR.

**Indicador 2, sin medir todavía:** los 3 despliegues hechos hasta hoy fueron manuales: el del 2026-10-28, ejecutando los pasos por separado, y los del 2026-10-29 y 2026-11-08, con `scripts/aws-encender.ps1`. `deploy.yml` está integrado desde el 2026-11-10 (DEP-C-05 · PR #46), pero solo corre desde `main` y todavía no se ha ejecutado. **Pendiente de decidir (equipo):** si el indicador cuenta desde la integración de `deploy.yml`, o si los despliegues anteriores entran en el total.

## Métricas de apoyo

| ID | Métrica | Fuente | Uso |
|---|---|---|---|
| M-01 | Tiempo de análisis de un CV | `duration_ms` en los logs JSON (DEV-C-08) | Complementa al OE1 |
| M-02 | Tasa de concordancia entre la recomendación de la IA y la decisión de RRHH | `decisiones_candidato.coincide_con_ia` | Evidencia de supervisión efectiva (DEC-009); una tasa cercana al 100% es ambigua y se declara así |
| M-03 | Cambio de recomendación entre ejecuciones del mismo CV | `medir_oe2` | Complementa al OE2. Con Qwen (2026-11-10): 0 cambios en los tres CV |
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
| Conteo automático de endpoints autenticados | TST-C-01 | 2 | **Hecho** (PR #32); medición en `docs/metricas/oe4_aislamiento.json` |
| Materiales de la medición manual del OE1 | TST-A-04 | 2 | **Hecho** (PR #36): `docs/metricas/oe1/` |
| Criterios ponderados en el prompt del análisis de CV (DEC-024) | DEV-C-14 | 3 | **Hecho** (PR #38) |
| Script de OE2 | TST-A-05 | 2 | **Hecho** (PR #35); por partes (PR #45) |
| Registros separados del OE2 por proveedor (DEC-026) | TST-A-06 | 3 | **Hecho** (PR #48); resultado de Qwen en `docs/metricas/oe2_qwen/` |
| Minutos promedio de revisión (OE1) y tasa de concordancia (M-02) en el dashboard | DEV-A-10 | 2 | **Hecho** (PR #29); se calculan en el backend (`GET /metricas/dashboard`) |
| Despliegue por `deploy.yml` (indicador 2 del OE4) | DEP-C-05 | 3 | **Integrado** (PR #46); falta su primera ejecución desde `main` |

## Registro de datos crudos

Cada medición guarda sus datos en `docs/metricas/` del repositorio (CSV o JSON) con fecha, SHA del commit y versión del modelo.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-14 | Borrador |
| 1.1 | 2026-10-18 | Aprobado: R1 (minutos-persona), R2 (cada integrante en una condición), R3 (tres CVs para OE2); historias y sprints asociados; métrica M-07 de la metodología; destino en el Capítulo IV según el índice oficial |
| 1.2 | 2026-10-27 | Estado de la instrumentación al cierre del Sprint 1: los cuatro requisitos del Sprint 1 están hechos; consulta del OE3 en `docs/metricas/` |
| 1.3 | 2026-11-03 | Medición del indicador 1 del OE4: 0 accesos cruzados y 100% de cobertura (TST-C-01 · PR #32); indicador 2 sin medir, con 2 despliegues manuales; OE1 y M-02 en el dashboard (PR #29); pendientes TST-A-04, TST-A-05 y DEP-C-05 |
| 1.4 | 2026-11-03 | Script del OE2 integrado (TST-A-05 · PR #35); primera corrida con 30 de 30 ejecuciones fallidas por la cuota gratuita de Gemini, registrada como intento; OE2 sin medir |
| 1.5 | 2026-11-03 | Materiales del OE1 integrados (TST-A-04 · PR #36); OE1 sin medir hasta DEV-C-14 (DEC-024, sin registrar) |
| 1.6 | 2026-11-04 | DEC-024 registrada e implementada (DEV-C-14 · PR #38): el OE1 ya puede medirse con la rúbrica de criterios ponderados, y la medición válida del OE2 se hará sobre el análisis con desglose |
| 1.7 | 2026-11-10 | **OE2 con dos registros separados (DEC-026, TST-A-06 · PR #48):** medido con Qwen3.8-Flash vía OpenRouter (desviación de 3,30, 4,22 y 3,05; cumple en los tres CV; M-03 sin cambios), Gemini sin corrida completa; OE2 por partes (PR #45); rutas nuevas en `docs/metricas/oe2_gemini/` y `oe2_qwen/`; OE4: tercer despliegue manual y `deploy.yml` integrado (PR #46), sin ejecutar. Versión publicada por Gabriel Llanos; el original de Diego Nina queda en `_historial` como v1.6 |
