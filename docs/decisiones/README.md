# Registro de decisiones (ADR)

Cada decisión de implementación se registra como `DEC-NNN` en formato ADR (*Architecture Decision Record*, registro de decisión de arquitectura): contexto, decisión, alternativas descartadas, trade-off aceptado, consecuencias y validación. Una decisión aprobada no se edita para cambiar su sentido: una decisión nueva la modifica o la reemplaza y lo indica.

| ID | Decisión | Registro |
|---|---|---|
| DEC-001 | Exclusión de la inferencia de emociones | Drive, doc 12 |
| DEC-002 | Rekognition solo para presencia y segunda persona, con consentimiento | Drive, doc 12 |
| DEC-003 | Confirmación humana de las decisiones de avance o descarte | Drive, doc 12 |
| DEC-004 | La Ruta A (Admin RRHH) va a E3 | Drive, roadmap (doc 11) |
| DEC-005 | Desarrollo en dos ciclos | Drive, roadmap (doc 11) |
| DEC-006 | Hito H-50 (50% del software) | Drive, roadmap (doc 11) |
| DEC-007 | Fórmula del score final | [DEC-007](DEC-007-formula-score-final.md) |
| DEC-008 | Frontend en TypeScript con contrato tipado | [DEC-008](DEC-008-frontend-typescript.md) |
| DEC-009 | Supervisión humana de las decisiones | [DEC-009](DEC-009-supervision-humana.md) |
| DEC-010 | Aislamiento en dos capas: aplicación + RLS | [DEC-010](DEC-010-rls-postgresql.md) |
| DEC-011 | JWT propio reforzado; Cognito como trabajo futuro | [DEC-011](DEC-011-autenticacion-jwt.md) |
| DEC-012 | Redis fuera del alcance | [DEC-012](DEC-012-redis-fuera-de-alcance.md) |
| DEC-013 | Correo de cierre a los descartados | [DEC-013](DEC-013-notificacion-descartados.md) |
| DEC-014 | Feed XML en la lista cerrada de operaciones del sistema | [DEC-014](DEC-014-feed-xml-lista-cerrada.md) |
| DEC-015 | Alta de empresas mediante un comando de administración | [DEC-015](DEC-015-alta-empresa-script.md) |
| DEC-016 | Procesamiento asíncrono con SQS + Lambda (punto 6 modificado por DEC-018) | [DEC-016](DEC-016-asincronia-sqs-lambda.md) |
| DEC-017 | Metodología: plan por fases con sprints semanales basados en Scrum | [DEC-017](DEC-017-metodologia-hibrida.md) |
| DEC-018 | Topología mínima en AWS sin NAT Gateway; dominio `vael.work` | [DEC-018](DEC-018-topologia-aws.md) |

La siguiente decisión usa el número DEC-019.
