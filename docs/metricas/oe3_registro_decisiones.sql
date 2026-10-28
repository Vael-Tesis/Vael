-- OE3 — Registro de las decisiones (doc 14). Tarea TST-C-04, historia HU-15.
--
-- Meta: 100 %. Fórmula: candidatos con fila en decisiones_candidato por etapa completada,
-- dividido entre los candidatos que completaron esa etapa. Condición adicional: el 100 % de
-- las decisiones contrarias a la IA tiene justificacion_humana.
--
-- Una etapa está completada cuando el estado del candidato solo se alcanza después de su
-- decisión humana (DEC-009). Los enums se guardan con el nombre en mayúsculas.
--
-- Cómo ejecutarla:
--   - Por empresa: como vael_app, con SET app.tenant_id = '<tenant>' (la RLS filtra).
--   - Toda la plataforma (medición final): como vael_system.
-- tests/test_invariante_decisiones.py ejecuta este mismo archivo en el CI.

-- 1. Cobertura por etapa
WITH completadas AS (
    SELECT c.id AS candidato_id, e.etapa
    FROM candidatos c
    CROSS JOIN (VALUES ('CV'), ('EXAMEN'), ('ENTREVISTA')) AS e(etapa)
    WHERE (e.etapa = 'CV' AND c.estado::text IN (
              'CV_APROBADO', 'CV_RECHAZADO', 'EXAMEN_PENDIENTE', 'EXAMEN_RENDIDO',
              'EXAMEN_POR_CONFIRMAR', 'EXAMEN_APROBADO', 'EXAMEN_RECHAZADO',
              'ENTREVISTA_PENDIENTE', 'ENTREVISTA_REALIZADA', 'FINALISTA', 'CONTRATADO', 'DESCARTADO'))
       OR (e.etapa = 'EXAMEN' AND c.estado::text IN (
              'EXAMEN_APROBADO', 'EXAMEN_RECHAZADO', 'ENTREVISTA_PENDIENTE', 'ENTREVISTA_REALIZADA',
              'FINALISTA', 'CONTRATADO', 'DESCARTADO'))
       OR (e.etapa = 'ENTREVISTA' AND c.estado::text IN ('FINALISTA', 'CONTRATADO', 'DESCARTADO'))
)
SELECT
    co.etapa,
    count(*) AS completaron,
    count(*) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM decisiones_candidato d
            WHERE d.candidato_id = co.candidato_id AND d.etapa::text = co.etapa
        )
    ) AS con_decision
FROM completadas co
GROUP BY co.etapa
ORDER BY co.etapa;

-- 2. Decisiones contrarias a la IA sin justificación (meta: 0)
SELECT count(*) AS contrarias_sin_justificacion
FROM decisiones_candidato
WHERE coincide_con_ia IS FALSE
  AND coalesce(btrim(justificacion_humana), '') = '';
