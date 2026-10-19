> COPIA del documento del Drive `VAEL/Docs/07_flujo_proceso.md`, versión 2.0, copiada el 2026-10-18.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 07 — Flujo del Proceso de Selección

| Campo | Valor |
|---|---|
| Versión | 2.0 |
| Actualizado | 2026-10-13 |
| Decisiones aplicadas | DEC-001, DEC-002, DEC-007, DEC-009, DEC-013 |
| Reemplaza | Versión 1 (2026-09-15): 20 etapas con filtros automáticos, política de silencio y análisis emocional |

## Principio rector

**La IA recomienda; RRHH decide (DEC-009).** El sistema automatiza el análisis, la generación y la calificación, pero ninguna decisión de avance o descarte se ejecuta sin la confirmación de una persona del equipo de RRHH, que queda registrada en `decisiones_candidato`. Esto responde a la calificación de riesgo alto del DS N.º 115-2025-PCM y al alcance comprometido en la sección 1.3 de la monografía.

El proceso tiene **19 etapas**, desde la postulación hasta el ranking y la decisión final de RRHH.

## Tabla resumen

| # | Etapa | Tipo | Notifica al candidato | Componente | Ruta |
|---|---|---|---|---|---|
| 1 | Postulación con aviso de uso de IA | Candidato | No | Router `publico` | B |
| 2 | Extracción del PDF | Automática | No | Servicio `analisis_cv` | A |
| 3 | Análisis IA del CV | Automática | No | Servicio `analisis_cv` + Gemini | A |
| 4 | Recomendación de CV | Automática | No | Servicio `analisis_cv` | A |
| 5 | **Decisión humana de CV** | **RRHH** | Sí: examen o cierre | Endpoint de decisiones + SES | A |
| 6 | Acceso al portal | Candidato | No | Router `evaluaciones` | B |
| 7 | Consentimiento y verificación de presencia | Candidato | No | Rekognition | B |
| 8 | Generación del examen | Automática | No | Servicio `examen` + Gemini | B |
| 9 | Rendición del examen | Candidato | No | Router `evaluaciones` | B |
| 10 | Calificación automática | Automática | No | Servicio `examen` + Gemini | B |
| 11 | Recomendación de examen | Automática | No | Servicio `examen` | B |
| 12 | **Decisión humana de examen** | **RRHH** | Sí: entrevista o cierre | Endpoint de decisiones + SES | A |
| 13 | Pool de preguntas de la entrevista | Automática | No | Servicio `entrevista_ia` + Gemini | B |
| 14 | Entrevista por voz con EVA | Candidato | No | Gemini Live API | B |
| 15 | Trigger de 5 minutos | Automática | No | Frontend del candidato | B |
| 16 | Supervisión de integridad | Automática | No | Rekognition | B |
| 17 | Análisis por dimensiones | Automática | No | Gemini | B |
| 18 | Cálculo del score final | Automática | No | Backend | A |
| 19 | **Ranking y decisión humana final** | **RRHH** | Sí: finalista o cierre | Router `candidatos` + SES | A |

La columna *Ruta* indica en qué ruta del roadmap se construye o revisa la etapa: A (Admin, ciclo actual) o B (Candidato, siguiente ciclo).

## Detalle de cada etapa

### 1. Postulación con aviso de uso de IA

El candidato accede a `/postular/{codigo}`, llena el formulario (nombre, apellidos, email, teléfono, pretensión salarial y LinkedIn opcionales) y sube su CV en PDF.

**Transparencia previa:** antes de enviar, el candidato recibe un aviso sobre el uso de inteligencia artificial, su finalidad y el tipo de recomendaciones que genera, y acepta el tratamiento de sus datos personales. (Implementación del aviso: DEV-B-01.)

Otras vías de ingreso: registro manual y carga masiva desde el panel de RRHH.

Resultado: candidato en estado `postulado`; CV en S3 en `cvs/{tenant_id}/...`.

### 2. Extracción del PDF

El servicio descarga el PDF desde S3 y extrae el texto con PyPDF2; si falla o devuelve texto vacío, usa pdfminer.six. Si ambos fallan, el candidato queda marcado con una inconsistencia para revisión manual.

### 3. Análisis IA del CV

Se ejecuta de forma asíncrona. Gemini recibe el texto del CV, los requisitos de la vacante, las habilidades y tecnologías, el nivel y los años de experiencia, la instrucción de IA del área y la instrucción extra de la vacante, y devuelve un JSON estructurado:

```json
{
  "score": 78,
  "clasificacion": "recomendado",
  "match_porcentaje": 82,
  "resumen": "Desarrollador con 3 años de experiencia en...",
  "habilidades_detectadas": ["Python", "FastAPI", "PostgreSQL", "Docker"],
  "inconsistencias": ["Gap de 8 meses entre 2023 y 2024 sin explicar"],
  "linkedin": "linkedin.com/in/usuario",
  "github": "github.com/usuario",
  "portfolio": null
}
```

Criterios del score (0-100): match de habilidades requeridas (0-40), años de experiencia (0-20), nivel educativo (0-15), coherencia del CV (0-15) y trayectoria profesional (0-10).

### 4. Recomendación de CV

El sistema compara `score_cv` con `score_cv_minimo` de la vacante (default 60) y genera una **recomendación**: `avanzar` si lo alcanza, `descartar` si no. El candidato pasa a `cv_por_confirmar`. **No se emite ningún token ni se envía ningún correo.**

### 5. Decisión humana de CV

RRHH revisa la recomendación en la **bandeja de recomendaciones por confirmar**: puntaje, umbral, recomendación y justificación de la IA.

- Si la decisión coincide con la recomendación, puede confirmarla de forma individual o en lote.
- Si no coincide, la decisión es individual y requiere una justificación escrita.
- Cada decisión queda registrada en `decisiones_candidato` con quién decidió, cuándo y cuánto tiempo tomó la revisión.

Efecto:
- **Avance** → estado `cv_aprobado`. Se emite el token de examen (JWT de 48 horas y código corto `VAEL-XXXX-XXXX`) y SES envía el correo con el link al examen.
- **Descarte** → estado `cv_rechazado`. SES envía un único correo genérico de cierre (DEC-013).

RRHH puede revertir una decisión registrando una decisión nueva; la anterior se conserva.

### 6. Acceso al portal del candidato

El candidato abre el link del correo; el frontend precarga el token. También puede ingresar el código corto, que el backend intercambia por el token (`resolver-codigo`). Si el token expiró, se muestra la pantalla de sesión expirada.

### 7. Consentimiento y verificación de presencia

Antes del examen, el candidato otorga su **consentimiento expreso** para la captura de imagen (Ley N.º 29733, DEC-002). Luego el sistema toma una foto y Rekognition verifica que haya exactamente un rostro visible, con un tamaño y una calidad mínimos.

Si la verificación falla, se pide repetirla; si falla de forma reiterada, el sistema permite continuar y registra un evento de auditoría (fail-open, para no bloquear a candidatos con problemas técnicos).

No se compara la identidad con un documento ni se analizan emociones (DEC-001).

Pendiente de la Ruta B (PLN-B-02): dónde se almacena esta captura, porque `capturas_auditoria` hoy exige una entrevista.

### 8. Generación del examen

Gemini genera 10 preguntas a partir del CV y de los requisitos de la vacante: 6 de opción múltiple con 4 alternativas y 4 abiertas. Solo pregunta por la intersección entre lo que declara el CV y lo que exige la vacante. Cada pregunta vale 2 puntos (máximo 20).

### 9. Rendición del examen

Duración de 45 minutos con timer regresivo, mapa de preguntas, autoguardado de cada respuesta y posibilidad de retomar si se corta la conexión. El proctoring está activo durante todo el examen (ver catálogo).

### 10. Calificación automática

Las preguntas de opción múltiple se comparan con la respuesta correcta (2 o 0 puntos). Las abiertas las califica Gemini con 0, 1 o 2 puntos y un `feedback_ia`. La nota es la suma, sobre 20. Se calcula el semáforo de integridad según el `puntaje_riesgo` acumulado.

### 11. Recomendación de examen

El sistema compara la nota con `nota_minima_examen` de la vacante (default 13) y genera la recomendación. El candidato pasa a `examen_por_confirmar`, sin emisión de token ni envío de correo.

### 12. Decisión humana de examen

Mismo mecanismo que la etapa 5. En la bandeja, RRHH ve además el semáforo de integridad del examen.

- **Avance** → `examen_aprobado`. Se emite el token de entrevista y SES envía la invitación, con la explicación de qué es EVA y recomendaciones de preparación.
- **Descarte** → `examen_rechazado`. Correo de cierre.

### 13. Pool de preguntas de la entrevista

Gemini genera entre 8 y 12 preguntas a partir del CV, los requisitos de la vacante, las dimensiones de la plantilla de evaluación y los resultados del examen. Cada pregunta tiene una prioridad (`critica`, `alta` o `media`); las críticas cubren las dimensiones de mayor peso.

Todas las entrevistas de una vacante usan la misma plantilla de dimensiones y criterios, lo que las hace estructuradas.

### 14. Entrevista por voz con EVA

El backend genera un token efímero de Gemini Live (`expireTime`: 30 minutos; `newSessionExpireTime`: 10 minutos). El frontend abre la sesión con ese token, captura el micrófono en PCM de 16 bits a 16 kHz y reproduce el audio de EVA en tiempo real. Latencia objetivo: menos de 1 segundo entre el fin de la intervención del candidato y la respuesta de EVA.

EVA saluda, explica la dinámica y conduce la entrevista con el pool de preguntas, con repreguntas cuando una respuesta es vaga. No revela puntuaciones. Si EVA no responde en 2 minutos, el frontend ofrece avanzar manualmente.

El canal definitivo (directo desde el navegador o mediante el backend) se decide en el ciclo 2.

### 15. Trigger de 5 minutos

Cuando quedan 5 minutos, **el frontend envía a la sesión de Gemini Live una instrucción de texto** con las preguntas críticas que aún no se formularon, para que EVA las adelante. Lo hace el frontend porque la sesión de voz es una conexión directa entre el navegador y Gemini: el backend no participa en ella. (Implementación: DEV-B-09.)

### 16. Supervisión de integridad

Cada 3 minutos el frontend toma una captura que se guarda en S3. Rekognition verifica dos cosas: que el rostro del candidato esté presente y que no haya una segunda persona. También se registra la detección de múltiples voces.

**No se analizan emociones faciales ni el sentimiento de las respuestas (DEC-001).** El reglamento peruano califica de riesgo alto a la inferencia de emociones en el entorno laboral, la Unión Europea la prohíbe en el reclutamiento y su fiabilidad científica es cuestionada (sección 1.3 de la monografía).

### 17. Análisis por dimensiones

Al terminar la entrevista, Gemini recibe la transcripción y las dimensiones de la plantilla. Asigna a cada dimensión una nota de 0 a 20 con su justificación, basada en el contenido de las respuestas.

Ejemplo con la plantilla Técnico Estándar:

```json
{
  "claridad_expresion": { "nota": 17, "peso": 20, "justificacion": "..." },
  "coherencia_respuestas": { "nota": 16, "peso": 20, "justificacion": "..." },
  "precision_tecnica": { "nota": 15, "peso": 30, "justificacion": "..." },
  "comunicacion_efectiva": { "nota": 18, "peso": 20, "justificacion": "..." },
  "seguridad_confianza": { "nota": 14, "peso": 10, "justificacion": "..." }
}
```

Nota de la entrevista = (17×0.20) + (16×0.20) + (15×0.30) + (18×0.20) + (14×0.10) = **16.1**

El candidato pasa a `entrevista_realizada`.

### 18. Cálculo del score final (DEC-007)

```
score_final = (score_cv / 5) × 0.20 + nota_examen × 0.40 + nota_entrevista × 0.40
```

Las tres notas quedan en escala 0-20 y el resultado se redondea a 2 decimales. Si falta alguna nota, `score_final` es nulo.

Ejemplo con CV 78, examen 15 y entrevista 16.1:
15.6 × 0.20 + 15 × 0.40 + 16.1 × 0.40 = 3.12 + 6.00 + 6.44 = **15.56**

Justificación de los pesos: la entrevista estructurada y las pruebas de conocimiento del puesto son los métodos de mayor validez predictiva según Sackett et al. (2022), muy por encima de la información derivada de la experiencia registrada en el CV. Los pesos están informados por esa evidencia, pero no validados para VAEL.

### 19. Ranking y decisión humana final

RRHH consulta el ranking de la vacante, ordenado por `score_final` descendente, con el desglose de CV, examen y entrevista. Los candidatos con proceso incompleto aparecen aparte. `top_candidatos_finalistas` sugiere cuántos finalistas marcar.

La decisión de la etapa `entrevista` se registra en `decisiones_candidato` como en las etapas 5 y 12:
- **Avanzar** → `finalista`. SES envía el correo de finalista con los próximos pasos.
- **Descartar** → `descartado`. Correo de cierre.

Las etapas posteriores (entrevista presencial, negociación, contratación) son manuales y quedan fuera del alcance.

## Catálogo de eventos de proctoring

| Evento | Severidad | Puntos de riesgo | Dónde aplica |
|---|---|---|---|
| perdida_foco | media | 3 | Examen |
| cambio_ventana | media | 4 | Examen |
| pantalla_dividida | media | 3 | Examen |
| inactividad | baja | 2 | Examen |
| copy_paste | alta | 6 | Examen |
| click_derecho | alta | 5 | Examen |
| devtools | alta | 8 | Examen |
| multiples_voces | alta | 10 | Entrevista |
| sin_rostro | alta | 8 | Entrevista |
| segunda_persona | alta | 10 | Entrevista |

## Semáforo de integridad

| Semáforo | Rango de puntaje | Interpretación | Acción sugerida |
|---|---|---|---|
| Verde | 0 a 6 | Sin incidencias significativas | Ninguna |
| Amarillo | 7 a 18 | Eventos menores | Revisión opcional por RRHH |
| Rojo | 19 o más | Eventos críticos acumulados | Revisión obligatoria antes de decidir |

El semáforo es informativo: nunca descalifica por sí mismo. Se muestra en la bandeja de decisiones para que RRHH lo considere.

## Política de notificaciones (DEC-013)

Regla: el candidato solo recibe correos como consecuencia de una **decisión humana**. Las recomendaciones de la IA no generan correos.

| Momento | ¿Se envía correo? |
|---|---|
| Postulación recibida | No |
| Recomendación de la IA (cualquier etapa) | No |
| Avance confirmado tras el CV | Sí — link al examen |
| Avance confirmado tras el examen | Sí — link a la entrevista |
| Avance confirmado tras la entrevista | Sí — correo de finalista |
| Descarte confirmado (cualquier etapa) | Sí — un único correo genérico de cierre, sin puntajes ni razones |
| Entrevista completada | No |

El correo de cierre agradece la postulación, informa que el proceso no continúa, indica que la evaluación usó inteligencia artificial con revisión humana e incluye un contacto de la empresa para consultas sobre datos personales.

RRHH puede reenviar el correo de la etapa actual con `/api/candidatos/{id}/reenviar-correo-etapa`; a un candidato descartado solo puede reenviarle el de cierre.

## Indicadores que produce el flujo

| Indicador | Fuente | Objetivo |
|---|---|---|
| Minutos de revisión por candidato | `decisiones_candidato.revision_inicio` y `decidido_en` | OE1 |
| Desviación estándar del score de un mismo CV en 10 ejecuciones | Etapa 3 | OE2 |
| Porcentaje de decisiones registradas y justificadas | `decisiones_candidato` | OE3 |
| Tasa de concordancia entre la recomendación de la IA y la decisión de RRHH | `decisiones_candidato.coincide_con_ia` | OE3 (supervisión efectiva) |

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1 | 2026-09-15 | Versión inicial: 20 etapas, filtros automáticos, política de silencio, análisis emocional y de sentimiento |
| 2.0 | 2026-10-13 | 19 etapas: los filtros automáticos pasan a recomendación más decisión humana (DEC-009), se eliminan el análisis emocional y el de sentimiento (DEC-001), consentimiento y verificación de presencia (DEC-002), fórmula 20/40/40 (DEC-007), política de notificaciones con correo de cierre (DEC-013), trigger de 5 minutos desde el frontend, indicadores por objetivo |
