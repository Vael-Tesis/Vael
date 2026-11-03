-- OE1 — Minutos de evaluación con VAEL (doc 14). Tarea TST-A-04, historia HU-25.
--
-- Indicador: minutos de evaluación humana por candidato CON VAEL = decidido_en - revision_inicio
-- en decisiones_candidato, etapa 'CV' (DEC-009). `revision_inicio` se fija cuando RRHH abre el
-- detalle de la recomendación en la bandeja (OE1, DEV-A-05); queda NULL si la decisión se tomó
-- sin pasar por ahí (por ejemplo, desde una prueba automática) — esas filas no cuentan para OE1.
--
-- Cómo ejecutarla:
--   - Acótala a los 10 candidatos de la muestra de esta corrida de TST-A-04 (CV-TI-01 a
--     CV-TI-10 contra TI-2026-001): agrega abajo los `candidato_id` exactos, o acota por
--     fecha con "AND decidido_en BETWEEN '<inicio de la sesión>' AND '<fin de la sesión>'".
--   - Por empresa: como vael_app, con SET app.tenant_id = '<tenant>' (la RLS filtra).
--   - Toda la plataforma (si hiciera falta): como vael_system.

-- 1. Detalle por candidato (para pegar junto a la planilla manual)
SELECT
    candidato_id,
    revision_inicio,
    decidido_en,
    ROUND(EXTRACT(EPOCH FROM (decidido_en - revision_inicio)) / 60.0, 2) AS minutos
FROM decisiones_candidato
WHERE etapa = 'CV'
  AND revision_inicio IS NOT NULL
  -- AND candidato_id IN ('<id_1>', '<id_2>', ...)  -- descomenta y completa con los 10 reales
ORDER BY decidido_en;

-- 2. Promedio y conteo (para la fórmula de reducción del OE1)
SELECT
    COUNT(*) AS candidatos,
    ROUND(AVG(EXTRACT(EPOCH FROM (decidido_en - revision_inicio)) / 60.0), 2) AS promedio_minutos_vael
FROM decisiones_candidato
WHERE etapa = 'CV'
  AND revision_inicio IS NOT NULL
  -- AND candidato_id IN ('<id_1>', '<id_2>', ...)  -- misma condición que arriba
;

-- 3. Fórmula de reducción (doc 14) — con el promedio_minutos_vael de la consulta 2 y el
--    promedio de "minutos" de docs/metricas/oe1/planilla_evaluacion_manual_*.csv:
--
--    reducción = 1 − (promedio_minutos_vael / promedio_minutos_manual)
--
--    Meta del OE1 (doc 14): reducción ≥ 50%.
