# Rúbrica de evaluación manual de CV — OE1 (TST-A-04, doc 14)

## Nota sobre los criterios (DEC-024)

Esta rúbrica usa los 5 criterios y pesos de **DEC-024**, que el equipo aprobó para que
`construir_prompt_analisis` implemente en el código el mismo desglose ponderado que ya
describía el doc 08 (match de habilidades 0-40, experiencia 0-20, formación 0-15, coherencia
0-15, trayectoria 0-10). Así la evaluación manual y `score_cv` puntúan con los mismos
criterios.

La evaluación manual del OE1 con esta rúbrica se hace **después de que DEV-C-14 esté
integrado** (la tarea que lleva DEC-024 al código), para que ambas condiciones midan la misma
tarea.

## Los 5 criterios ponderados (doc 08), total 0–100

Antes de calificar, lee la ficha de la vacante (TI-2026-001, Desarrollador Backend Python,
`docs/diseno/13_datos_semilla.md`):

| Campo | Valor |
|---|---|
| Nivel buscado | Semi senior |
| Requisitos obligatorios | 3 años o más con Python y una base de datos relacional |
| Requisitos deseables | No se especificaron |
| Habilidades/tecnologías buscadas | Python, FastAPI, PostgreSQL, Docker, pytest |
| Instrucción del área (Tecnología) | Valorar la profundidad técnica demostrable y los proyectos verificables |
| Umbral de avance (`score_cv_minimo`) | 60 / 100 |

### Criterio 1 — Match de habilidades (0–40)

¿Cuántas de las habilidades/tecnologías buscadas (Python, FastAPI, PostgreSQL, Docker,
pytest) aparecen evidenciadas en el CV, con uso real y no solo mencionadas de pasada?

| Puntos | Nivel | Descripción |
|---|---|---|
| 33–40 | Completo | 4 o 5 de las 5 buscadas, con evidencia de uso (proyectos, funciones, responsabilidades) |
| 21–32 | Mayoría | 3 de las 5, con evidencia de uso |
| 9–20 | Parcial | 1 o 2 de las 5, o varias mencionadas solo de nombre sin evidencia de uso |
| 0–8 | Casi nulo | Ninguna de las 5, o solo tecnologías sin relación con el stack buscado |

### Criterio 2 — Experiencia (0–20)

¿Los años y el tipo de experiencia encajan con el nivel buscado (semi senior, 3+ años con
Python y una base de datos relacional)?

| Puntos | Nivel | Descripción |
|---|---|---|
| 16–20 | Cumple o supera | Iguala o supera los años y el nivel pedidos, en roles directamente relevantes |
| 11–15 | Cumple con matices | Cumple los años pedidos, pero el nivel o el tipo de rol no calzan del todo |
| 6–10 | Cumple parcialmente | Menos años de los pedidos, o experiencia solo tangencialmente relacionada |
| 0–5 | No cumple | Muy por debajo del nivel o los años pedidos, o experiencia en otro dominio |

### Criterio 3 — Formación (0–15)

¿La formación académica o las certificaciones son relevantes para el puesto y están descritas
de forma verificable (institución, título, fechas)?

| Puntos | Nivel | Descripción |
|---|---|---|
| 12–15 | Relevante y verificable | Carrera o certificación afín a desarrollo de software, con institución y fechas identificables |
| 8–11 | Relevante, poco detallada | Formación afín, pero sin institución o fechas claras |
| 4–7 | Tangencial | Formación en un área relacionada pero no directamente afín (p. ej. otra ingeniería) |
| 0–3 | Sin formación relevante | No se menciona formación, o es ajena por completo al puesto |

### Criterio 4 — Coherencia (0–15)

¿El CV se lee como un relato profesional **coherente y bien organizado** — las secciones se
conectan entre sí y se entiende la progresión del candidato? (Esto es sobre la *organización
del relato*, no sobre fechas o hechos contradictorios: eso se registra aparte, como
inconsistencias — ver la sección siguiente.)

| Puntos | Nivel | Descripción |
|---|---|---|
| 12–15 | Coherente | El relato se sigue con facilidad de principio a fin, sin secciones desconectadas |
| 8–11 | Mayormente coherente | Se entiende en general, pero alguna sección está mal organizada o es difícil de ubicar en la línea de tiempo |
| 4–7 | Cuesta seguirlo | Faltan conexiones entre roles o secciones; hay que inferir bastante |
| 0–3 | Confuso | El CV no tiene un orden reconocible o es contradictorio en su organización |

### Criterio 5 — Trayectoria (0–10)

¿La progresión de responsabilidades y logros a lo largo del tiempo muestra crecimiento
profesional concreto?

| Puntos | Nivel | Descripción |
|---|---|---|
| 8–10 | Progresión clara | Responsabilidades y logros crecientes, descritos de forma concreta |
| 5–7 | Progresión razonable | Hay progresión, pero los logros se describen de forma general |
| 2–4 | Trayectoria plana | Los roles no muestran crecimiento, o los logros son vagos |
| 0–1 | Sin trayectoria reconocible | CV muy corto o sin roles claros que permitan evaluar progresión |

## Inconsistencias detectadas — observación, no suma al puntaje

Además de los 5 criterios, registra aparte (columna `inconsistencias_observadas` de la
planilla) cualquier inconsistencia que notes al leer el CV: fechas superpuestas, vacíos sin
explicar, afirmaciones que no calzan con el resto del documento, logros no verificables, etc.
**Esto es una observación cualitativa, igual que el campo `inconsistencias` que produce VAEL
— no resta ni suma puntos a ningún criterio.** Si no notas ninguna, anota "Ninguna".

## Puntaje final y decisión

1. Suma los 5 criterios (40 + 20 + 15 + 15 + 10 = 100 posibles). Ese es el equivalente manual
   de `score_cv`.
2. Clasificación final, por el puntaje total (para que quede un solo criterio de corte,
   consistente con las 4 categorías de `clasificacion_ia`):

   | Puntaje total | Clasificación |
   |---|---|
   | 80–100 | Altamente recomendado |
   | 60–79 | Recomendado |
   | 40–59 | Requiere revisión |
   | 0–39 | No apto |

3. **Decisión** (lo que registra la planilla): **Avanzar** si el puntaje total es **≥ 60**
   (`score_cv_minimo` de TI-2026-001); **Descartar** en caso contrario — la misma regla que
   aplica el servicio de decisiones de VAEL (`score_cv >= score_cv_minimo`, DEC-009).

> Las bandas de clasificación (80/60/40) son una convención de esta rúbrica para que el
> corte sea reproducible entre evaluadores; lo que se compara en el OE1 es el **tiempo**, no
> el acuerdo entre el puntaje manual y el de VAEL.
