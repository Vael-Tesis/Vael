# DEC-013 — Notificación de cierre a los candidatos descartados

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-02 (decisión 7) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Reemplaza | "Política de silencio" del doc 07 (no notificar rechazos) |
| Depende de | DEC-009 (el descarte lo confirma RRHH) |

## Contexto

- **HECHO (doc 07 y `services/correos.py`):** rige una política de silencio: nunca se envía un correo de rechazo, y las funciones de correo lo impiden de forma expresa para `cv_rechazado` y `examen_rechazado`.
- **HECHO:** el candidato descartado en la etapa de CV no recibe ningún token, por lo que tampoco puede consultar su progreso en el portal. No recibe respuesta alguna.
- **HECHO (monografía E2 v1.1):** la Tabla 2.2 define para los candidatos la estrategia "mantener informado"; la Tabla 2.5 establece que el análisis automatizado de currículums se trata como elaboración de perfiles, "con información al candidato". La política de silencio contradice ambas.
- **SUPUESTO por verificar en la fuente primaria:** la Ley N.º 29733 reconoce al titular un derecho frente a decisiones basadas únicamente en el tratamiento automatizado de sus datos. Con DEC-009 la decisión deja de ser únicamente automatizada; informar al candidato refuerza el cumplimiento.

## Decisión

1. **Momento:** el correo se envía únicamente cuando RRHH confirma un descarte mediante el endpoint de decisiones (DEC-009), en cualquiera de las etapas (CV, examen o entrevista). Nunca se envía a partir de una recomendación de la IA sin confirmar.
2. **Contenido:**
   - Agradecimiento por la postulación y nombre de la vacante.
   - Aviso de que el proceso no continúa.
   - Transparencia: en la evaluación se utilizó inteligencia artificial con revisión humana.
   - Un contacto de la empresa cliente para consultas sobre el tratamiento de los datos personales.
3. **Exclusiones:** el correo no incluye puntajes, notas, razones del descarte ni justificaciones generadas por la IA.
4. **Envío único:** un solo correo de cierre por candidato y vacante. Si RRHH revierte el descarte (fila nueva con `reemplaza_a`), el proceso continúa con los correos normales de avance.
5. **Guardas:** el bloqueo de `correos.py` se reemplaza por una regla más precisa: a un candidato en estado de descarte solo se le puede enviar la plantilla de cierre; los correos de avance siguen bloqueados para ese estado.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| A. Mantener la política de silencio | Contradice las Tablas 2.2 y 2.5 entregadas y deja a los descartados en la etapa de CV sin ninguna respuesta |
| C. Correo con retroalimentación detallada | Expone justificaciones de la IA que pueden contener errores (sección 2.3.2), aumenta el riesgo de reclamos y revela los criterios de evaluación |
| D. Política configurable por empresa | Amplía el alcance sin aportar a ningún objetivo específico |

## Trade-off aceptado

El candidato sabe que no continúa, pero no por qué. Se prioriza no exponer razonamientos de la IA sin verificar frente a una retroalimentación más rica. La consulta individual queda canalizada por el contacto de la empresa.

## Consecuencias

Cambios en el roadmap:

| Tarea | Cambio |
|---|---|
| DEV-C-10 (DEC-009) | El endpoint de decisiones dispara el correo de cierre al confirmar un descarte |
| Servicio de correos | Nueva plantilla `correo_cierre_proceso`; guardas actualizadas según el punto 5 |

Documentos a actualizar:
- Doc 07: política de notificaciones (se elimina la política de silencio) y tabla "¿Se envía correo?".
- Doc 08: catálogo de correos y regla de negocio crítica.
- Doc 06: comportamiento del endpoint de decisiones.
- `CLAUDE.md`: política de notificaciones.

## Validación

- Test: confirmar un descarte envía exactamente un correo de cierre.
- Test: una recomendación de descarte sin confirmar no envía correo.
- Test: el correo de cierre no contiene puntaje, nota ni texto de la justificación de la IA.
- Test: a un candidato descartado no se le puede enviar ningún correo de avance.
- Test: confirmar dos veces el mismo descarte no duplica el correo (idempotencia).
