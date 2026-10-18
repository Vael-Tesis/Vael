# DEC-009 — Supervisión humana de las decisiones de avance y descarte

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-02 (decisión adicional, prioridad P0 tras la re-auditoría de la línea base) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Implementa | DEC-003 (doc 12): las decisiones de avance o descarte requieren confirmación humana |
| Reemplaza | Filtros automáticos de las etapas 4 y 11 del doc 07 |
| Relacionada con | DEC-007 (el score final es una recomendación, no una decisión); OE3 |

## Contexto

Compromisos ya entregados en la monografía (E1 y E2 v1.1):
- Sección 1.3: "Ninguna decisión de avance o descarte se ejecuta sin confirmación humana". El perfil de RRHH permite "confirmar o revertir las recomendaciones de avance y descarte".
- OE3: registrar el 100% de las decisiones de avance o descarte con el criterio aplicado, el puntaje obtenido y su justificación, de forma consultable y auditable.
- Tabla 2.5: el DS N.º 115-2025-PCM califica de riesgo alto a la IA aplicada a la selección de personal y exige supervisión humana, transparencia algorítmica y registro del funcionamiento del sistema.

Estado del código al 2026-10-13 (HECHOS):
- `services/analisis_cv.py` cambia el estado a `cv_aprobado` (y emite token y correo) o a `cv_rechazado` sin intervención humana.
- `services/examen.py` hace lo mismo con `examen_aprobado` / `examen_rechazado`.
- La decisión posterior a la entrevista ya es manual (`marcar-finalista`), pero no deja registro.
- `POST /api/candidatos/{id}/cambiar-estado` permite cualquier transición sin registrar autor ni justificación.
- No existe ninguna tabla de decisiones.

## Decisión

1. **La IA recomienda; RRHH decide.** Se agregan los estados `cv_por_confirmar` y `examen_por_confirmar`. Al terminar el análisis del CV o la calificación del examen, el sistema registra el puntaje y una recomendación (`avanzar` / `descartar`), pero no cambia a un estado de avance o descarte, no emite tokens y no envía correos. Esas acciones se ejecutan solo cuando RRHH confirma un avance.
2. **Puntos de decisión:** CV, examen y entrevista. En la entrevista, la decisión es marcar como finalista o descartar.
3. **Registro de solo inserción:** tabla `decisiones_candidato`. Ninguna fila se edita ni se borra.

   | Campo | Contenido |
   |---|---|
   | `id`, `tenant_id`, `candidato_id` | Identificación y aislamiento por empresa |
   | `etapa` | `cv` / `examen` / `entrevista` |
   | `recomendacion_ia` | `avanzar` / `descartar` (nulo en la etapa de entrevista si no hay umbral) |
   | `puntaje`, `umbral` | Puntaje obtenido y criterio aplicado (por ejemplo, `score_cv_minimo` = 60) |
   | `justificacion_ia` | Justificación generada por la IA |
   | `decision` | `avanzar` / `descartar` |
   | `coincide_con_ia` | Si la decisión sigue la recomendación |
   | `justificacion_humana` | **Obligatoria** cuando `coincide_con_ia` es falso |
   | `decidido_por`, `decidido_en` | Usuario de RRHH y fecha y hora |
   | `revision_inicio` | Momento en que RRHH abrió la recomendación, para medir minutos de evaluación (OE1) |
   | `reemplaza_a` | Si RRHH revierte una decisión, se crea una fila nueva que apunta a la anterior |

4. **Confirmación en lote restringida:** RRHH puede confirmar varias recomendaciones a la vez solo cuando la decisión coincide con la recomendación. Toda decisión contraria a la IA es individual y requiere justificación escrita.
5. **Un solo camino para decidir:** las transiciones de avance y descarte solo se ejecutan a través del endpoint de decisiones. `cambiar-estado` deja de aceptar esos estados.
6. **Permisos:** deciden los roles reclutador, admin y gerente. El rol evaluador solo consulta.
7. **Notificaciones:** se mantiene la política vigente (solo se notifica a quien avanza). La política hacia los descartados se decide por separado (PLN-C-02, decisión 7).

Endpoints nuevos (a especificar en el doc 06):
- `GET /api/candidatos/por-confirmar?vacante_id=&etapa=` — bandeja de recomendaciones pendientes.
- `POST /api/candidatos/{id}/decision` — decisión individual.
- `POST /api/candidatos/decisiones/lote` — confirmación en lote (solo decisiones que coinciden con la IA).
- `GET /api/candidatos/{id}/decisiones` — historial de decisiones del candidato.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| A. Decisión automática con reversión posterior por RRHH | La decisión se ejecuta antes de la intervención humana; contradice la sección 1.3 |
| B. Confirmación humana solo para descartes; avances automáticos | Contradice la sección 1.3 ("avance o descarte"); exigiría modificar un capítulo entregado |

## Trade-off aceptado

- **Tiempo de espera del candidato:** entre el CV y el examen, y entre el examen y la entrevista, ahora media una confirmación humana. No afecta al OE1, que mide minutos de evaluación por candidato y no el tiempo total del proceso; el tiempo de confirmación de RRHH sí se registra como minutos de evaluación.
- **Sesgo de automatización:** la confirmación en lote puede derivar en aprobación sin revisión. Se mitiga con la regla 4 y se mide con la **tasa de concordancia** (porcentaje de recomendaciones confirmadas frente a revertidas). Una tasa cercana al 100% es ambigua: puede indicar una IA acertada o una revisión superficial. Esta ambigüedad se declara como limitación en el Capítulo III.

## Consecuencias

Cambios en el roadmap:

| Tarea | Cambio |
|---|---|
| DEV-C-10 (nueva) | Modelo y migración de `decisiones_candidato` y de los nuevos estados; modificación de `analisis_cv.py` y `examen.py`; endpoints de decisiones; restricción de `cambiar-estado` |
| DEV-A-05 / DEV-A-06 | Bandeja de recomendaciones por confirmar y historial de decisiones en el detalle del candidato |
| TST-C (nueva prueba) | Ningún candidato llega a un estado de avance o descarte sin su fila en `decisiones_candidato` (evidencia del OE3) |
| PLN-C-06 | Agregar al plan de métricas la tasa de concordancia y los minutos de revisión |

Documentos a actualizar:
- Doc 05: enum de estados y tabla `decisiones_candidato`.
- Doc 06: endpoints nuevos y restricción de `cambiar-estado`.
- Doc 07: etapas 4, 11 y 20 (de filtro automático a recomendación más confirmación).
- Doc 08: flujos de `analizar_cv` y `calificar_examen`.
- `CLAUDE.md`: regla de que la IA nunca ejecuta decisiones.
- Monografía, Capítulo III: presentar la decisión con sus alternativas y la limitación sobre el sesgo de automatización.

Pendiente de verificar: si el prototipo Figma incluye la pantalla de bandeja de confirmación. Si no la incluye, se diseña antes de DEV-A-05.

## Validación

- Test: tras el análisis del CV o la calificación del examen, el candidato queda en `*_por_confirmar`, sin token emitido ni correo enviado.
- Test: confirmar un avance emite el token y envía el correo; confirmar un descarte no envía correo.
- Test: una decisión contraria a la recomendación sin `justificacion_humana` se rechaza (422).
- Test: la confirmación en lote rechaza cualquier decisión que no coincida con la recomendación.
- Test: `cambiar-estado` rechaza los estados de avance y descarte.
- Indicador OE3: candidatos con al menos una fila en `decisiones_candidato` por cada etapa que completaron, dividido entre los candidatos que completaron esa etapa = 100%.
