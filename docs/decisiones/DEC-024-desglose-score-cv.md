# DEC-024 — Desglose ponderado y auditable del `score_cv`

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-11-03 |
| Tarea de origen | TST-A-04 (hallazgo al preparar la medición del OE1); se implementa en DEV-C-14 |
| Decidido por | Equipo (Diego Nina); registrada por Diego Nina |
| Corrige | Doc 08 (sección de análisis de CV), que describía desde su versión 1 un desglose que el código no implementaba |
| Relacionada con | DEC-009 (supervisión humana), DEC-001 (sin emociones); OE1 y OE2 (doc 14) |

## Contexto

- **HECHO:** `construir_prompt_analisis` (`app/services/analisis_cv.py`) le pide a Gemini un único `score` de 0 a 100 por juicio global, sin criterios ni desglose.
- **HECHO:** el doc 08 describe desde su versión 1 un puntaje con cinco criterios ponderados: match de habilidades (0-40), experiencia (0-20), formación (0-15), coherencia (0-15) y trayectoria (0-10). El código nunca lo implementó.
- La propuesta de valor (doc 02) y la monografía presentan una evaluación con criterios **auditables por RRHH**, en un sistema diseñado para la normativa peruana de IA de riesgo alto. Un puntaje global sin desglose no permite explicar por qué un candidato queda por encima o por debajo del umbral de la recomendación.
- La medición del OE2 (consistencia del puntaje) todavía no se realizó, y la del OE1 necesita una rúbrica manual que haga la misma tarea que VAEL.

## Decisión

1. **El prompt pide cinco puntajes por criterio**, cada uno con su rango y una justificación breve:

   | Criterio | Rango |
   |---|---|
   | Match de habilidades | 0 a 40 |
   | Experiencia | 0 a 20 |
   | Formación | 0 a 15 |
   | Coherencia | 0 a 15 |
   | Trayectoria | 0 a 10 |

2. **El backend valida y suma.** Verifica que estén los cinco criterios, que sean enteros y que cada uno esté dentro de su rango, y calcula `score_cv` como la suma. El puntaje total no depende de que el modelo sume bien.
3. **Si la respuesta no cumple** (falta un criterio o un valor está fuera de rango), el análisis se trata como fallido por el camino de error que ya existe; no se ajustan valores en silencio.
4. **El desglose se guarda** en un campo nuevo del candidato (`score_desglose`, JSON con puntaje y justificación por criterio) y **se muestra en el detalle del candidato**, junto al puntaje total.
5. **Los candidatos analizados antes de esta decisión** quedan con `score_desglose` nulo, y la pantalla lo indica ("análisis anterior al desglose").
6. Los pesos son **fijos para todo el sistema** en esta versión. La instrucción de IA por área y por vacante sigue orientando el criterio de match. Hacer los pesos configurables por empresa queda como trabajo futuro y se declara así.
7. La `clasificacion_ia` sigue viniendo del modelo, sin cambios en esta decisión.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Corregir solo el doc 08 y mantener el puntaje global | Contradice la diferenciación declarada (criterios auditables) y deja el OE1 sin una tarea comparable |
| Pedirle al modelo el desglose y también el total | El total podría no coincidir con la suma; el backend tendría que elegir cuál creer |
| Pesos configurables por empresa ahora | Agrega configuración, pantallas y validaciones sin tiempo para hacerlo bien antes de E3 |

## Trade-off aceptado

- El prompt pide más estructura, lo que puede aumentar levemente el tiempo de respuesta y la probabilidad de una respuesta inválida; se mitiga con la validación y el camino de error existente.
- Los pesos fijos no permiten que cada empresa priorice criterios distintos; se declara como limitación.

## Consecuencias

| Elemento | Cambio |
|---|---|
| DEV-C-14 (nueva tarea, HU-12) | Prompt, validación y suma, campo `score_desglose` con su migración, tests y pantalla de detalle |
| Doc 05 | Campo `Candidato.score_desglose` |
| Doc 06 | `score_desglose` en la respuesta del candidato |
| Doc 08 | Sección de análisis de CV corregida: describe lo implementado |
| Doc 16 | CA de RF-A-10: el análisis muestra el desglose por criterio |
| Doc 02 y monografía | La afirmación de criterios auditables queda respaldada; se declara que los pesos son fijos |
| OE1 (TST-A-04) | La rúbrica manual usa los mismos cinco criterios y pesos |
| OE2 (TST-A-05) | Se mide **después** de DEV-C-14, sobre el sistema con desglose |

## Validación

- Test: una respuesta válida produce `score_cv` igual a la suma de los cinco criterios.
- Test: un criterio faltante o fuera de rango hace fallar el análisis por el camino de error, sin guardar un puntaje.
- Test: el detalle del candidato expone `score_desglose`; un candidato anterior lo expone como nulo.
- El análisis de un CV real en el navegador muestra los cinco criterios con su justificación.
