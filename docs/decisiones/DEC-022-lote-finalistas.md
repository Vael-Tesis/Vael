# DEC-022 — Recomendación de finalistas con `top_candidatos_finalistas`

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-28 |
| Tarea de origen | DEV-A-06 (HU-18, Sprint 2) |
| Decidido por | Gabriel Llanos (Product Owner); registrada por Diego Nina (Scrum Master) |
| Modifica | DEC-009, punto 2 (decisiones de la etapa `entrevista`) |
| Relacionada con | DEC-007 (score final), DEC-013 (correo de cierre) |

## Contexto

- DEC-009 permite confirmar en lote **solo las decisiones que coinciden con la recomendación de la IA**, y exige justificación cuando RRHH decide lo contrario.
- En las etapas de CV y examen, la recomendación sale de un umbral (`score_cv_minimo`, `nota_minima_examen`).
- En la etapa de **entrevista no hay umbral**: la tabla `decisiones_candidato` admite `recomendacion_ia` nulo en esa etapa. Sin recomendación, la confirmación en lote de finalistas (RF-A-15, HU-18) no tiene con qué coincidir, y cada decisión exigiría justificación.
- La vacante ya tiene el campo `top_candidatos_finalistas` (default 5), definido como la cantidad sugerida de finalistas.

## Decisión

1. En la etapa `entrevista`, el sistema genera una **recomendación** para cada candidato con `score_final` (DEC-007):
   - `avanzar` si está entre los primeros `top_candidatos_finalistas` del ranking de su vacante.
   - `descartar` en caso contrario.
2. Los candidatos con proceso incompleto (`score_final` nulo) **no reciben recomendación** y no entran en el lote.
3. **Empates en el último puesto:** todos los candidatos empatados con el puntaje del puesto N reciben `avanzar`. La regla prefiere no excluir a nadie por un orden arbitrario.
4. Con esa recomendación se aplica sin cambios la regla de DEC-009: la confirmación en lote solo admite decisiones que coinciden con la recomendación; decidir lo contrario es individual y requiere justificación.
5. La recomendación se recalcula cada vez que se consulta el ranking, porque depende del conjunto de candidatos con proceso completo. Se registra en `decisiones_candidato` (puntaje, posición y valor de `top_candidatos_finalistas` como umbral) en el momento de la decisión.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Umbral de nota mínima para la entrevista | Agrega un parámetro nuevo a la vacante; el ranking relativo es más útil cuando el número de puestos es fijo |
| Sin recomendación en la entrevista; decisiones solo individuales con justificación | Contradice RF-A-15 (finalistas en lote) y vuelve lenta la selección final |
| Lote sin restricción en la etapa de entrevista | Rompe la regla de DEC-009: permitiría confirmar en lote decisiones sin referencia de la IA |

## Trade-off aceptado

La recomendación depende de la posición relativa: un mismo candidato puede pasar de `avanzar` a `descartar` si se completan procesos de candidatos con mejor puntaje. Por eso se fija en `decisiones_candidato` el contexto del momento en que se decidió.

## Consecuencias

| Elemento | Cambio |
|---|---|
| DEV-A-06 (HU-17, HU-18) | Cálculo de la recomendación en el ranking; confirmación en lote de finalistas |
| Doc 05 | `umbral` en la etapa `entrevista` guarda `top_candidatos_finalistas`; la posición y el criterio quedan en `justificacion_ia` (no se agrega una columna nueva) |
| Doc 07, etapa 19 | Recomendación de finalistas según el ranking |
| Doc 08 | Servicio de decisiones: recomendación de la etapa `entrevista` |
| Doc 16 | CA de RF-A-15 con la regla de empates |
| Roadmap | Sección 4: DEC-022 registrada; HU-18 desbloqueada |

## Validación

- Test: con `top_candidatos_finalistas` = 3 y cinco candidatos completos, los tres de mayor `score_final` reciben `avanzar` y los otros dos `descartar`.
- Test: un empate en el tercer puesto da `avanzar` a todos los empatados.
- Test: un candidato con `score_final` nulo no recibe recomendación ni entra en el lote.
- Test: el lote rechaza una decisión que no coincide con la recomendación.
