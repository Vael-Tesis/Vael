# Procedimiento — Medición del OE1 (TST-A-04, doc 14)

Indicador: **minutos de evaluación humana por candidato** en la etapa de CV. Línea base:
evaluación manual cronometrada de los 10 CV de la muestra, con la rúbrica de
`rubrica_evaluacion_manual_cv.md`. Medición con VAEL: `decidido_en − revision_inicio` en
`decisiones_candidato` (consulta en `oe1_minutos_vael.sql`). Meta: reducción ≥ 50%.

**Este documento prepara el procedimiento; no contiene resultados.** Las personas del equipo
hacen la evaluación cronometrada y completan la planilla — no se inventa ni se completa aquí
(CLAUDE.md, sección 2.4; doc 17, sección 5.3: ninguna cifra sin fuente verificable).

## 0. Antes de empezar — decisión R2 (obligatoria)

**R2 (doc 14, aprobado en la revisión):** para no contaminar la medición con el aprendizaje
de haber visto antes el mismo CV, **cada integrante del equipo evalúa en una sola condición**:

- **Una persona** evalúa los 10 CV **a mano**, con la rúbrica y la planilla de este
  directorio. Es quien produce el dato de la línea base (minutos manuales).
- **La otra persona** hace que los 10 CV pasen por **VAEL** (registro + análisis real con
  Gemini) y, luego, por la bandeja de recomendaciones — ella no evalúa los CV a mano.

Decidan y registren aquí, antes de empezar, quién hace cada condición (editen esta sección
al ejecutar la tarea; no se completa de antemano):

| Condición | Responsable |
|---|---|
| Evaluación manual (los 10 CV) | _(pendiente de asignar)_ |
| Registro y análisis con VAEL (los 10 CV) | _(pendiente de asignar)_ |

**Regla dura:** quien evalúa manualmente **no debe haber visto el análisis de IA de ningún
CV de la muestra** antes de terminar su evaluación manual de los 10. Si ya se ejecutó el
análisis con VAEL antes de esta tarea (por ejemplo, en una demo), esa persona queda
descartada como evaluadora manual para esta muestra.

## 1. Evaluación manual (hazlo primero, completo, antes del paso 2)

1. Copia `planilla_evaluacion_manual_PLANTILLA.csv` a un archivo nuevo con tu nombre, por
   ejemplo `planilla_evaluacion_manual_rocio.csv`, y pon tu nombre en la columna `evaluador`
   de cada fila.
2. Abre la rúbrica (`rubrica_evaluacion_manual_cv.md`) y la ficha de la vacante que trae (la
   misma rúbrica ya la incluye; es TI-2026-001, Desarrollador Backend Python).
3. Para cada uno de los 10 CV, **en el orden de la tabla de la sección 3** (no lo cambies: el
   orden también es parte de lo reproducible):
   1. Anota la **hora de inicio** (hora local, formato `HH:MM:SS`) justo antes de abrir el CV.
   2. Lee el CV completo (ubicación: sección 3) y aplica los 5 criterios ponderados de la
      rúbrica (match de habilidades 0–40, experiencia 0–20, formación 0–15, coherencia 0–15,
      trayectoria 0–10).
   3. Anota el puntaje de cada criterio en su propia columna, respetando el máximo de cada
      uno (no los 5 comparten la misma escala).
   4. Anota aparte, en la columna `inconsistencias_observadas`, cualquier inconsistencia que
      notes (fechas superpuestas, vacíos sin explicar, afirmaciones que no calzan) — es una
      observación cualitativa, **no resta ni suma puntos** a ningún criterio. Si no notas
      ninguna, escribe "Ninguna".
   5. Calcula el puntaje total (suma de los 5 criterios, máximo 100) y la decisión (Avanzar si
      ≥ 60, Descartar si no — regla de la rúbrica).
   6. Anota la **hora de fin** justo al terminar de registrar la decisión de ese CV (no al
      terminar de leer: el tiempo de registrar también es parte del minuto medido, igual que
      en VAEL se mide hasta `decidido_en`).
   7. Calcula los minutos (`hora_fin − hora_inicio`) y anótalos.
4. No evalúes los 10 de una sola sentada si eso no refleja cómo trabajarías normalmente
   (puedes pausar entre CV); lo que importa es que el cronómetro de cada CV sea limpio
   (inicio real → fin real de ese CV, sin incluir la pausa).
5. Guarda el CSV. No edites los minutos "a mano" después de calculados: si te equivocaste de
   hora, anota la corrección en la columna `notas`, no borres el dato original.

## 2. Registro y análisis con VAEL (después de que el paso 1 esté completo)

1. Con el entorno local levantado (CLAUDE.md, sección 15) y las semillas cargadas (doc 13),
   registra cada uno de los 10 CV como candidato de TI-2026-001 — por la pantalla de
   "Registrar candidato" (carga individual o masiva) o por `POST /api/candidatos`, igual que
   lo haría RRHH.
2. Deja que el análisis real de Gemini corra para los 10 (sin mocks).
3. Desde la **bandeja de recomendaciones**, abre el detalle de cada uno (eso fija
   `revision_inicio`) y confirma o decide la recomendación — igual que en RF-A-11. No hace
   falta cronometrar nada a mano aquí: `revision_inicio` y `decidido_en` ya quedan en
   `decisiones_candidato`.
4. Corre `oe1_minutos_vael.sql` (consultas 1 y 2) para obtener el detalle y el promedio de
   minutos con VAEL.

## 3. Muestra: los 10 CV (CV-TI-01 a CV-TI-10)

Del doc 13 (TI-2026-001, Desarrollador Backend Python). **No se usan CV-TI-11 ni CV-TI-12**
(escaneado y dañado): son los casos de error de RF-A-09, no de la muestra del OE1.

| # | CV | Perfil (doc 13) | Ubicación del texto fuente | Ubicación del PDF |
|---|---|---|---|---|
| 1 | CV-TI-01 | 5 años con Python, FastAPI y PostgreSQL (score alto) | `backend/seeds/cvs_texto/CV-TI-01.txt` | `backend/seeds/cvs/CV-TI-01.pdf` |
| 2 | CV-TI-02 | 4 años con Django y MySQL (score alto) | `backend/seeds/cvs_texto/CV-TI-02.txt` | `backend/seeds/cvs/CV-TI-02.pdf` |
| 3 | CV-TI-03 | 3 años con Python y proyectos en GitHub (medio-alto) | `backend/seeds/cvs_texto/CV-TI-03.txt` | `backend/seeds/cvs/CV-TI-03.pdf` |
| 4 | CV-TI-04 | 2 años con Java y algo de Python (caso límite, ≈60) | `backend/seeds/cvs_texto/CV-TI-04.txt` | `backend/seeds/cvs/CV-TI-04.pdf` |
| 5 | CV-TI-05 | Recién egresado con prácticas en Python (límite) | `backend/seeds/cvs_texto/CV-TI-05.txt` | `backend/seeds/cvs/CV-TI-05.pdf` |
| 6 | CV-TI-06 | 6 años con PHP, sin Python (bajo → descartar) | `backend/seeds/cvs_texto/CV-TI-06.txt` | `backend/seeds/cvs/CV-TI-06.pdf` |
| 7 | CV-TI-07 | Diseñador gráfico sin experiencia técnica (muy bajo) | `backend/seeds/cvs_texto/CV-TI-07.txt` | `backend/seeds/cvs/CV-TI-07.pdf` |
| 8 | CV-TI-08 | 5 años con Python, con un vacío de 14 meses (inconsistencia) | `backend/seeds/cvs_texto/CV-TI-08.txt` | `backend/seeds/cvs/CV-TI-08.pdf` |
| 9 | CV-TI-09 | Fechas laborales superpuestas (inconsistencia) | `backend/seeds/cvs_texto/CV-TI-09.txt` | `backend/seeds/cvs/CV-TI-09.pdf` |
| 10 | CV-TI-10 | Líder técnico, 12 años (sobrecalificación) | `backend/seeds/cvs_texto/CV-TI-10.txt` | `backend/seeds/cvs/CV-TI-10.pdf` |

Los `.txt` están versionados en el repositorio. Los `.pdf` **no** (`.gitignore`): si no
existen todavía en tu copia, regenéralos con:

```bash
cd backend
python -m app.scripts.generar_cvs
```

Para la evaluación **manual**, cualquiera de los dos formatos sirve (el texto es el mismo);
para el **registro en VAEL** hace falta el PDF, porque el candidato se registra subiendo un
archivo.

## 4. Al terminar

1. Ambos CSV completos (`planilla_evaluacion_manual_<nombre>.csv`, con los 10 CV, sus
   puntajes, sus horas y sus minutos) quedan en `docs/metricas/oe1/`.
2. El resultado de `oe1_minutos_vael.sql` (promedio y detalle) se guarda también en
   `docs/metricas/oe1/` — por ejemplo `oe1_minutos_vael_resultado.csv` o `.json`, exportado de
   la consulta, con la fecha y el SHA del commit (doc 14, "Registro de datos crudos").
3. Con el promedio manual (de la planilla) y el promedio VAEL (de la consulta), calcula la
   reducción: `1 − (promedio_vael / promedio_manual)`, y compárala con la meta (≥ 50%).
4. Registra el resultado final en `docs/validacion/` o en el doc 14, con la misma honestidad
   que pide doc17 — incluida la amenaza a la validez de la muestra pequeña y ficticia (10 CV),
   ya declarada en la sección 1.3 de la monografía.
