> COPIA del documento del Drive `VAEL/Docs/08_servicios_negocio.md`, versión 2.2, copiada el 2026-10-28.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 08 — Servicios de Negocio

| Campo | Valor |
|---|---|
| Versión | 2.2 |
| Actualizado | 2026-10-27 |
| Fuente de verdad | Código en `backend/app/services/`, `backend/app/core/` y `backend/app/scripts/` (revisado al cierre del Sprint 1, 2026-10-27) + DEC-001, DEC-002, DEC-007, DEC-009, DEC-010, DEC-013, DEC-015, DEC-016, DEC-018 |
| Copia en el repositorio | `docs/diseno/08_servicios_negocio.md` (DEC-019). La fuente es este documento |

Los servicios contienen la lógica de negocio y no dependen de FastAPI. Estados: **Implementado** · **Cambia (tarea · historia)** · **Planificado (tarea · historia)** · **Se elimina (tarea)**. Lo integrado en el Sprint 1 indica la tarea y el PR.

## Reglas transversales

1. **La IA recomienda; nunca decide (DEC-009).** Ningún servicio de análisis cambia a un estado de avance o descarte, emite tokens ni envía correos al candidato. Eso solo lo hace el servicio de decisiones. Lo verifica `tests/test_invariante_decisiones.py` (TST-C-04 · PR #14): un análisis estático falla si otro módulo asigna esos estados.
2. **Aislamiento (DEC-010).** Toda tarea fuera de una petición HTTP recibe el `tenant_id` y lo fija antes de tocar la base de datos.
3. **Sin inferencia de emociones (DEC-001).**
4. **Asincronía con despachador único (DEC-016).** Ningún código llama a SQS ni a `BackgroundTasks` directamente: usa `despachar_tarea(tipo, payload)`.
5. **Las Lambdas no acceden a la base de datos (DEC-018).** Reciben en el mensaje todo lo que necesitan, calculan con Gemini y entregan el resultado al backend por `/api/interno/...`.

## Arquitectura del procesamiento asíncrono (DEC-016 y DEC-018)

Cada análisis se divide en dos funciones:

| Parte | Dónde corre | Qué hace | Toca la base de datos |
|---|---|---|---|
| **Cálculo** (`calcular_*`) | Lambda en producción; en proceso en desarrollo | Descarga el archivo de S3 si corresponde, construye el prompt con los datos del mensaje y llama a Gemini | **No** |
| **Aplicación** (`aplicar_resultado_*`) | Backend | Valida, fija el tenant, guarda el resultado, genera la recomendación y verifica la idempotencia | Sí, como `vael_app` |

```
backend ──despachar_tarea──▶ SQS ──▶ Lambda (calcular_*) ──HMAC──▶ /api/interno/resultados/* ──▶ aplicar_resultado_*
          (desarrollo: en proceso, sin SQS ni HTTP)
```

El mensaje incluye: `tenant_id`, identificadores, key del archivo en S3 y los datos del prompt (requisitos, habilidades, instrucciones de IA del área y de la vacante). Así la Lambda no necesita consultar la base de datos.

## core/despacho.py — Implementado en modo en proceso (DEV-C-13 · PR #8); SQS planificado (HU-23)

| Función | Descripción |
|---|---|
| `despachar_tarea(tipo, payload)` | **Hoy:** valida que el payload traiga `tenant_id` y el identificador del `tipo` (`TipoTarea`, `CAMPO_ID`) y ejecuta el análisis en el mismo proceso. **Planificado (HU-23):** en producción publica en la cola SQS del `tipo`; en desarrollo y tests ejecuta `calcular_*` y `aplicar_resultado_*` en el mismo proceso |

Colas: `vael-analisis-cv` y `vael-analisis-entrevista`, cada una con su DLQ (cola de mensajes fallidos).

## core/gemini.py — Implementado (DEV-C-04 · PR #7)

| Función | Descripción |
|---|---|
| `consultar_gemini_json(prompt, model_name=None)` | Llama a Gemini pidiendo JSON y lo parsea |
| `como_lista_str(valor)` | Normaliza listas devueltas por el modelo |

Usa `google-genai` (`google-generativeai` se eliminó), con el ID de modelo verificado, registro del modelo y los parámetros de cada llamada (OE2) y **reintento con backoff exponencial ante 429 y 503** (`MAX_INTENTOS = 4`, espera base de 2 s).

## core/scoring.py — Implementado (DEV-C-01 · PR #4)

`calcular_score_final(score_cv, nota_examen, nota_entrevista)` con las constantes `PESO_CV = 0.20`, `PESO_EXAMEN = 0.40` y `PESO_ENTREVISTA = 0.40` (DEC-007); `null` si falta alguna nota.

## core/logs.py — Implementado (DEV-C-07/08 · PR #6)

`configurar_logging` emite JSON con `tenant_id`, `candidato_id`, `operation` y `duration_ms`; `medir_operacion` mide la duración de una operación.

## core/proctoring.py — Implementado

`calcular_semaforo(puntaje_riesgo)`: verde ≤ 6, amarillo 7–18, rojo ≥ 19. Catálogo de eventos: doc 07.

## core/interno.py — Planificado (DEV-C-13 · HU-23)

| Función | Descripción |
|---|---|
| `verificar_firma(cuerpo, marca_tiempo, firma)` | HMAC-SHA256 con el secreto de Secrets Manager; rechaza firmas inválidas y marcas de más de 5 minutos |
| `firmar(cuerpo)` | Usada por las Lambdas para firmar su entrega |

## services/analisis_cv.py

| Función | Estado | Descripción |
|---|---|---|
| `extraer_texto_pdf(pdf_bytes)` | Implementado | PyPDF2; si falla o queda vacío, pdfminer.six |
| `construir_prompt_analisis(texto_cv, vacante, area)` | Implementado. **Cambia (HU-23):** recibirá los datos de la vacante como diccionario, no como objeto de la base de datos | Texto del CV, requisitos, habilidades, tecnologías, nivel, instrucciones de IA; exige JSON puro |
| `calcular_analisis_cv(mensaje)` | **Planificado (HU-23)** | Parte de cálculo: descarga el PDF, extrae el texto, llama a Gemini y devuelve el resultado. Sin base de datos |
| `aplicar_resultado_analisis_cv(resultado, tenant_id)` | **Planificado (HU-23)** | Guarda score, clasificación, resumen, habilidades, inconsistencias y enlaces; genera la recomendación según `score_cv_minimo`; deja `cv_por_confirmar`. No emite tokens ni envía correos |
| `analizar_cv(...)` y `analizar_cv_candidato(...)` | Implementados | Ya cumplen DEC-009 (DEV-C-10 · PR #13): guardan el análisis y dejan `cv_por_confirmar`, sin tokens ni correos. Un CV sin texto extraíble (escaneado) no va a Gemini: queda en `cv_por_confirmar` como `requiere_revision` (DEV-A-05). **Se reemplazan (HU-23)** por las dos funciones anteriores |

Criterios del score (0-100): match de habilidades (0-40), experiencia (0-20), formación (0-15), coherencia (0-15), trayectoria (0-10). Respuesta esperada: doc 07, etapa 3.

## services/examen.py

| Función | Estado | Descripción |
|---|---|---|
| `generar_preguntas(...)` | Implementado | 6 de opción múltiple y 4 abiertas sobre la intersección CV–vacante |
| `calificar_examen(examen_id, db)` | Implementado (DEV-C-10 · PR #13) | Opción múltiple 2/0; abiertas 0/1/2 con Gemini; nota sobre 20; semáforo; deja `examen_por_confirmar` (la recomendación la calcula el servicio de decisiones con `nota_minima_examen`) |
| `registrar_evento(...)` | Implementado | Crea el evento y suma el puntaje de riesgo |

## services/entrevista_ia.py

| Función | Estado | Descripción |
|---|---|---|
| `generar_token_efimero_live()` | Implementado | `expireTime` 30 min; `newSessionExpireTime` 10 min |
| `generar_pool_preguntas(...)` | Implementado | 8 a 12 preguntas con prioridad |
| `construir_system_instruction(...)` | Implementado. **Cambia (DEV-B-11, ciclo siguiente):** del voseo al español neutro | Comportamiento de EVA |
| `analizar_entrevista(...)` | Implementado; `score_final` con DEC-007 (DEV-C-01 · PR #4). **Cambia (HU-23):** se divide en `calcular_analisis_entrevista` (Lambda) y `aplicar_resultado_analisis_entrevista` (backend) | Nota por dimensión con justificación; deja `entrevista_realizada` |

## services/decisiones.py — Implementado (DEV-C-10 · PR #13 · HU-15, HU-16)

Único servicio autorizado a ejecutar avances y descartes.

| Función | Descripción |
|---|---|
| `recomendacion_de_etapa(...)` / `calcular_recomendacion(...)` | Recomendación de la IA para la etapa: CV con `score_cv_minimo`, examen con `nota_minima_examen`; entrevista sin umbral (recomendación nula) |
| `registrar_decision(...)` | Valida la etapa, exige justificación si no coincide (422), inserta en `decisiones_candidato` y ejecuta el efecto. Repetir la decisión vigente es idempotente; cambiarla inserta una decisión nueva con `reemplaza_a` (así se revierte; no hay una función aparte). Al descartar invalida los tokens del candidato |
| `registrar_decisiones_lote(...)` | Todo o nada; solo decisiones que coinciden con la recomendación |
| `recomendaciones_pendientes(...)` | Bandeja: candidatos en `*_por_confirmar` con su recomendación |
| `historial(...)` | Decisiones del candidato, en orden |

Constantes: `ESTADO_POR_CONFIRMAR`, `ESTADO_RESULTANTE` y `ESTADOS_DE_DECISION_HUMANA` (los usa `cambiar-estado` para rechazar esos estados).

**Pendiente (HU-18, DEV-A-06):** criterio del lote en la etapa `entrevista`; propuesta: `top_candidatos_finalistas` (DEC-022).

| Etapa | Avanzar | Descartar |
|---|---|---|
| `cv` | `cv_aprobado` + token + `correo_bienvenida_examen` | `cv_rechazado` + `correo_cierre_proceso` |
| `examen` | `examen_aprobado` + token + `correo_invitacion_entrevista` | `examen_rechazado` + `correo_cierre_proceso` |
| `entrevista` | `finalista` + `correo_finalista` | `descartado` + `correo_cierre_proceso` |

## services/correos.py

| Función | Estado |
|---|---|
| `correo_bienvenida_examen`, `correo_invitacion_entrevista`, `correo_finalista`, `correo_credenciales_usuario` | Implementados |
| `correo_cierre_proceso(candidato, vacante, empresa)` | Implementado (DEV-C-10 · PR #13, DEC-013): agradecimiento, cierre del proceso, uso de IA con revisión humana y `Empresa.email_contacto` para datos personales; sin puntajes ni razones. Devuelve si se envió |

Guarda de envío (`ESTADOS_DESCARTE`): a un candidato rechazado o descartado nunca se le envía un correo de avance; solo `correo_cierre_proceso`. Repetir la decisión vigente es idempotente, así que no se reenvía. Los correos de avance aceptan la vacante para nombrarla en el texto. Remitente en producción: `noreply@vael.work` (DEC-018).

## services/vacantes.py — Implementado (DEV-A-04 · PR #20 · HU-08, HU-09, HU-10)

| Función | Descripción |
|---|---|
| `cambiar_estado(vacante, destino)` | Aplica `TRANSICIONES` (ver doc 05); 409 si no es válida; `cerrada` es final |
| `eliminar_vacante(vacante)` | Solo en estado `borrador` y sin candidatos; 409 en otro caso |
| `guardar_textos_publicacion(vacante, textos)` | Persiste `textos_publicacion` |

`services/vacante_ia.py` — `generar_textos_marketing(vacante)` — Implementado.

## services/candidatos.py — Implementado (DEV-A-01 · PR #17, DEV-A-05 · PR #21); banco de talento planificado (DEV-A-08 · HU-14)

| Función | Descripción |
|---|---|
| `editar_nota`, `eliminar_nota` | Solo el autor edita; el autor o un admin eliminan; actualiza `updated_at` |
| `etiquetas_de`, `asignar_etiqueta`, `quitar_etiqueta`, `eliminar_tag` | Asignación idempotente; borrar una etiqueta borra sus asignaciones |
| `motivo_de_rechazo_cv(nombre, contenido)` | Valida el CV antes de subirlo: no vacío, hasta 10 MB, extensión y firma de PDF, y que se pueda abrir. Un PDF escaneado sí se acepta (va a revisión manual). La carga masiva devuelve el motivo de cada archivo fallido |
| Banco de talento | **Planificado (DEV-A-08 · HU-14)** |

## services/sesiones.py — Implementado (DEV-A-02 · PR #18, DEC-011)

| Función | Descripción |
|---|---|
| `crear_sesion(usuario)` | Crea la fila en `sesiones` y devuelve el refresh token (solo se guarda su SHA-256) |
| `rotar(claims, refresh_token, usuario)` | Revoca la sesión usada y crea otra; si el token ya estaba revocado, revoca todas las del usuario (`SesionInvalida`) |
| `cerrar(...)` | Logout: revoca la sesión |
| `revocar_todas(usuario_id, tenant_id)` | Al desactivar al usuario o cambiar su contraseña |

## services/aws_services.py

| Función | Estado |
|---|---|
| `validar_identidad`, `detectar_segunda_persona` | Implementados (verificación de presencia; ciclo siguiente) |
| ~~`detectar_emociones`, `analizar_sentimiento`~~ | **Eliminados (DEV-C-12 · PR #5, DEC-001)** |
| `transcribir_audio` | Implementado, sin uso (se decide en el ciclo siguiente) |
| `subir_archivo`, `descargar_archivo`, `generar_url_prefirmada` | Implementados (S3; URLs de 1 hora) |
| `enviar_correo` | Implementado (SES) |
| `encolar_tarea` | Implementado, sin uso. Lo usará `despachar_tarea` en producción |

## scripts/ — Implementado

| Script | Tarea | Descripción |
|---|---|---|
| `crear_roles` | DEV-C-11 · PR #10 | Crea `vael_owner`, `vael_app` y `vael_system` (DEC-010) |
| `crear_empresa` | DEV-C-03 · PR #15 (DEC-015) | Crea la empresa y su administrador como `vael_app`, con contraseña temporal enviada por correo. El `tenant_id` es un UUID v5 de la razón social normalizada (`tenant_de`), así no necesita ver otras empresas ni ampliar la lista cerrada. Idempotente |
| `semillas` | DEV-C-03 · PR #15 | Carga los datos del doc 13 (empresas A y B, usuarios por rol, áreas, plantillas, vacantes y los datos de la empresa testigo B). Contraseñas desde `SEED_PASSWORD` o `SEED_PASSWORD_<ROL>`; reutiliza `crear_empresa`. Idempotente |
| `generar_cvs` | DEV-C-03 · PR #15 | Genera los PDF de los CV ficticios desde `backend/seeds/cvs_texto/`, incluidos el escaneado (CV-TI-11) y el dañado (CV-TI-12) |
| `exportar_openapi` | DEV-C-09 · PR #16 (DEC-008) | Exporta el OpenAPI a `frontend/openapi.json` para generar el cliente tipado |

## Consideraciones transversales

- **Idempotencia:** SQS entrega cada mensaje al menos una vez; `aplicar_resultado_*` y el servicio de decisiones no duplican filas, tokens ni correos.
- **Logs:** JSON con `tenant_id`, `candidato_id`, operación y `duration_ms` (DEV-C-08).
- **Cuota de Gemini:** con reintento y backoff (DEV-C-04); si se agota, el mensaje vuelve a la cola y, tras los reintentos, termina en la DLQ con alarma.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1 | 2026-09-15 | Versión inicial |
| 2.0 | 2026-10-13 | Alineado con el código real; servicio de decisiones; correo de cierre; brechas |
| 2.1 | 2026-10-18 | División cálculo/aplicación para las Lambdas (DEC-016, DEC-018); despachador; firma HMAC; reintento ante 429 asignado a DEV-C-04; servicios de vacantes y candidatos de la retrospectiva; script de alta de empresa (DEC-015); remitente `vael.work`; referencias a historias de usuario |
| 2.2 | 2026-10-27 | Cierre del Sprint 1: implementados despachador en proceso, `google-genai` con reintento, score, logs JSON, servicio de decisiones, correo de cierre, sesiones, vacantes, candidatos y scripts. Emociones eliminadas. La división cálculo/aplicación y la firma HMAC quedan para HU-23. Pendiente: lote de la etapa entrevista (DEC-022) |
