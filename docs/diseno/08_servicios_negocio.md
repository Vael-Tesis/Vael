> COPIA del documento del Drive `VAEL/Docs/08_servicios_negocio.md`, versión 3.2, copiada el 2026-11-10.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 08 — Servicios de Negocio

| Campo | Valor |
|---|---|
| Versión | 3.2 |
| Actualizado | 2026-11-10 |
| Fuente de verdad | Código en `backend/app/services/`, `backend/app/core/` y `backend/app/scripts/` (revisado tras el Sprint 2, 2026-11-03) + DEC-001, DEC-002, DEC-007, DEC-009, DEC-010, DEC-013, DEC-015, DEC-016, DEC-018, DEC-022, DEC-024, DEC-025, DEC-026 |
| Copia en el repositorio | `docs/diseno/08_servicios_negocio.md` (DEC-019). La fuente es este documento |

Los servicios contienen la lógica de negocio y no dependen de FastAPI. Estados: **Implementado** · **Cambia (tarea · historia)** · **Planificado (tarea · historia)** · **Se elimina (tarea)**. Lo integrado en los Sprints 1 y 2 indica la tarea y el PR.

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

El mensaje incluye: `tipo`, `tenant_id`, identificadores, key del archivo en S3 y los datos del prompt (requisitos, habilidades, instrucciones de IA del área y de la vacante). Así la Lambda no necesita consultar la base de datos. **Implementado (DEV-C-13 · HU-23 · PR #42).** La Lambda (`app/lambda_handler.py`, imagen `backend/Dockerfile.lambda`) recibe sus claves de un secreto propio, sin las URL de la base de datos, e informa los mensajes fallidos con `ReportBatchItemFailures`. Tras 3 intentos, un mensaje termina en la DLQ y su alarma de CloudWatch se dispara.

## core/despacho.py — Implementado (DEV-C-13 · PR #8 y PR #42)

| Función | Descripción |
|---|---|
| `despachar_tarea(tipo, payload)` | Valida que el payload traiga `tenant_id` y el identificador del `tipo` (`TipoTarea`, `CAMPO_ID`). Según `DESPACHO_MODO`: con `en_proceso` (desarrollo y tests, por defecto), ejecuta preparación, cálculo y aplicación en el mismo proceso; con `sqs` (AWS), prepara el mensaje con la sesión `vael_app` y el tenant fijado, y lo publica en la cola del `tipo` (`SQS_URL_ANALISIS_CV`, `SQS_URL_ANALISIS_ENTREVISTA`) |

Colas: `vael-analisis-cv` y `vael-analisis-entrevista`, cada una con su DLQ (cola de mensajes fallidos).

## core/gemini.py — Implementado (DEV-C-04 · PR #7; respaldo en DEV-C-15 · PR #44)

| Función | Descripción |
|---|---|
| `consultar_gemini_json(prompt, model_name=None, permitir_respaldo=True)` | Punto único de las llamadas de texto con salida JSON. Llama a Gemini pidiendo JSON y lo parsea. **Respaldo (DEC-025, PR #44):** con `IA_PROVEEDOR=qwen` llama directamente a Qwen; con `IA_RESPALDO=qwen`, si Gemini agota sus reintentos por un error de disponibilidad (429, 503, 504 o tiempo límite), repite la llamada con Qwen y lo registra en el log. Un error que no es de disponibilidad (por ejemplo, una clave inválida) no pasa a Qwen. `permitir_respaldo=False` lo desactiva: lo usa la medición del OE2, que mide Gemini |
| `como_lista_str(valor)` | Normaliza listas devueltas por el modelo |

Usa `google-genai` (`google-generativeai` se eliminó), con el ID de modelo verificado, registro del modelo y los parámetros de cada llamada (OE2) y **reintento con backoff exponencial ante 429, 503 y 504** (`MAX_INTENTOS = 4`, espera base de 2 s) y **tiempo límite de 60 s por llamada** (`TIEMPO_LIMITE_SEGUNDOS`, observación de TST-A-01 · PR #23). Desde el PR #44, ese ciclo vive en `_consultar_gemini` y `consultar_gemini_json` lo envuelve con el respaldo. Los servicios no cambian: siguen llamando a `consultar_gemini_json`, así que el respaldo cubre el análisis de CV, el examen, la entrevista y los textos de vacantes, y también la Lambda. La entrevista por voz (Gemini Live) no tiene respaldo.

## core/qwen.py — Implementado (DEV-C-15 · PR #44, DEC-025)

| Función | Descripción |
|---|---|
| `consultar_qwen_json(prompt)` | `POST {QWEN_BASE_URL}/chat/completions` (API compatible con OpenAI: el Open WebUI de Tecsup u OpenRouter) con una instrucción de sistema que exige solo JSON; hasta 3 intentos ante 429, 500, 502, 503 y 504, y 90 s por llamada |
| `extraer_json(texto)` | Quita el razonamiento `<think>…</think>` de Qwen3, los bloques de markdown y el texto alrededor del objeto, y lo parsea |
| `listar_modelos()` | Lista los modelos del servidor (lo usa `probar_qwen`) |
| `qwen_configurado()` | True si hay `QWEN_BASE_URL` y `QWEN_MODEL` |

El servidor de Tecsup está en una IP privada: **solo responde desde la red del campus**. Por eso, con ese servidor, el respaldo sirve con VAEL en local dentro del campus. Con OpenRouter (`https://openrouter.ai/api/v1`, modelo `qwen/qwen3.8-flash`, de pago; DEC-026) responde desde cualquier red. En AWS el respaldo solo se configura con `-ConQwen`.

## core/scoring.py — Implementado (DEV-C-01 · PR #4)

`calcular_score_final(score_cv, nota_examen, nota_entrevista)` con las constantes `PESO_CV = 0.20`, `PESO_EXAMEN = 0.40` y `PESO_ENTREVISTA = 0.40` (DEC-007); `null` si falta alguna nota.

## core/logs.py — Implementado (DEV-C-07/08 · PR #6)

`configurar_logging` emite JSON con `tenant_id`, `candidato_id`, `operation` y `duration_ms`; `medir_operacion` mide la duración de una operación.

## core/proctoring.py — Implementado

`calcular_semaforo(puntaje_riesgo)`: verde ≤ 6, amarillo 7–18, rojo ≥ 19. Catálogo de eventos: doc 07.

## core/interno.py — Implementado (DEV-C-13 · PR #42)

| Función | Descripción |
|---|---|
| `verificar_firma(cuerpo, marca_tiempo, firma)` | HMAC-SHA256 de `"<marca>." + cuerpo` con `INTERNAL_SERVICE_KEY` (Secrets Manager); rechaza firmas inválidas y marcas con más de 5 minutos de diferencia (`VENTANA_SEGUNDOS`) |
| `firmar(cuerpo, marca_tiempo=None)` | Usada por la Lambda: devuelve la marca y la firma para las cabeceras `X-Vael-Marca-Tiempo` y `X-Vael-Firma` |

## services/analisis_cv.py

| Función | Estado | Descripción |
|---|---|---|
| `extraer_texto_pdf(pdf_bytes)` | Implementado | PyPDF2; si falla o queda vacío, pdfminer.six |
| `datos_prompt_vacante(vacante, area)` y `construir_prompt_analisis(texto_cv, datos)` | Implementados (DEV-C-14 · PR #38; PR #42). El prompt recibe los datos de la vacante como diccionario; su texto es idéntico al anterior (verificado), así que el OE2 sigue siendo comparable | Texto del CV, requisitos, habilidades, tecnologías, nivel, instrucciones de IA; pide los cinco criterios ponderados (puntaje + justificación por criterio), sin pedir el total; exige JSON puro |
| `_validar_y_sumar_desglose(criterios)` | Implementado (DEV-C-14 · HU-12, DEC-024) | Valida que estén los cinco criterios y que cada puntaje sea un entero dentro de su rango; `score_cv` es su suma. Si algo no cumple, lanza el error que deja al análisis como fallido (ver más abajo) |
| `preparar_mensaje_analisis_cv(candidato, vacante, area)` | Implementado (PR #42) | Parte de preparación (backend): el mensaje de SQS |
| `calcular_analisis_cv(mensaje)` | Implementado (PR #42) | Parte de cálculo: descarga el PDF de S3, extrae el texto, llama a Gemini, valida y suma el desglose (DEC-024). Si no hay texto, devuelve `sin_texto` sin llamar a la IA. Sin base de datos |
| `aplicar_resultado_analisis_cv(candidato, resultado, db)` | Implementado (PR #42) | Guarda score, desglose, clasificación, resumen, habilidades, inconsistencias y enlaces, y deja `cv_por_confirmar`; la recomendación según `score_cv_minimo` la calcula el servicio de decisiones. No emite tokens ni envía correos. Idempotente: solo aplica si el candidato está en `postulado` o `cv_analizando` |
| `analizar_cv(...)` y `analizar_cv_candidato(...)` | Implementados | Modo en proceso: encadenan preparación, cálculo y aplicación. Cumplen DEC-009 (DEV-C-10 · PR #13). Un CV sin texto extraíble (escaneado) no va a Gemini: queda en `cv_por_confirmar` como `requiere_revision` (DEV-A-05). Si el cálculo falla, el candidato vuelve a `postulado` |

**Corregido (DEV-C-14 · PR #38, DEC-024):** desde su versión 1, este documento describía un desglose ponderado del score (match de habilidades 0-40, experiencia 0-20, formación 0-15, coherencia 0-15, trayectoria 0-10) que el código nunca implementó: el prompt pedía a Gemini un único puntaje global. DEC-024 corrigió el código: `construir_prompt_analisis` pide los cinco criterios por separado, cada uno con una justificación breve, y `_validar_y_sumar_desglose` calcula `score_cv` como su suma, sin depender de que el modelo sume bien. El desglose se guarda en `Candidato.score_desglose` (doc 05) y se muestra en el detalle del candidato (doc 06; RF-A-10 del doc 16). Los pesos son fijos para todo el sistema en esta versión; hacerlos configurables por empresa queda como trabajo futuro.

Respuesta esperada: doc 07, etapa 3.

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
| `analizar_entrevista(transcripcion, dimensiones)` | Implementado (DEV-C-01 · PR #4; PR #42) | Nota por dimensión con justificación. Recibe las dimensiones como diccionarios (`datos_dimension`) |
| `preparar_mensaje_analisis_entrevista`, `calcular_analisis_entrevista` y `aplicar_resultado_analisis_entrevista` | Implementados (PR #42) | Preparación (backend), cálculo (Lambda, sin base de datos) y aplicación (backend): guarda la nota, calcula `score_final` con DEC-007 y deja `entrevista_realizada`. Idempotente: no aplica si la entrevista ya tiene nota |

## services/decisiones.py — Implementado (DEV-C-10 · PR #13 · HU-15, HU-16)

Único servicio autorizado a ejecutar avances y descartes.

| Función | Descripción |
|---|---|
| `recomendacion_de_etapa(...)` / `calcular_recomendacion(...)` | Recomendación de la IA para la etapa: CV con `score_cv_minimo`, examen con `nota_minima_examen`; entrevista con `top_candidatos_finalistas` (DEC-022, DEV-A-06 · PR #27): nula mientras el candidato no tenga `score_final` |
| `ranking_vacante(vacante_id, tenant_id)` | **Implementado (DEV-A-06 · PR #27).** Candidatos de la vacante con `score_final`, de mayor a menor (DEC-007). Lo usan `GET /candidatos/ranking` y la recomendación de la entrevista |
| `recomendaciones_finalistas(ranking, top)` | **Implementado (DEV-A-06 · PR #27).** `avanzar` para los primeros `top` puestos, con los empates del puesto `top`; `descartar` para el resto. Se recalcula en cada consulta |
| `registrar_decision(...)` | Valida la etapa, exige justificación si no coincide (422), inserta en `decisiones_candidato` y ejecuta el efecto. Repetir la decisión vigente es idempotente; cambiarla inserta una decisión nueva con `reemplaza_a` (así se revierte; no hay una función aparte). Al descartar invalida los tokens del candidato |
| `registrar_decisiones_lote(...)` | Todo o nada; solo decisiones que coinciden con la recomendación |
| `recomendaciones_pendientes(...)` | Bandeja: candidatos en `*_por_confirmar` con su recomendación |
| `historial(...)` | Decisiones del candidato, en orden |

Constantes: `ESTADO_POR_CONFIRMAR`, `ESTADO_RESULTANTE` y `ESTADOS_DE_DECISION_HUMANA` (los usa `cambiar-estado` para rechazar esos estados).

**Lote de finalistas (HU-18) — Implementado (DEV-A-06 · PR #27, DEC-022):** en la etapa `entrevista`, el lote acepta solo las decisiones que coinciden con la recomendación por `top_candidatos_finalistas`.

`registrar_decision(..., enviar_correos=False)` registra la decisión y cambia el estado sin enviar el correo de la etapa. Solo lo usa el script de semillas (DEV-A-07 · PR #28), para que encender el entorno en AWS no envíe correos por SES a direcciones `@example.com`.

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

## services/candidatos.py — Implementado (DEV-A-01 · PR #17, DEV-A-05 · PR #21)

| Función | Descripción |
|---|---|
| `editar_nota`, `eliminar_nota` | Solo el autor edita; el autor o un admin eliminan; actualiza `updated_at` |
| `etiquetas_de`, `asignar_etiqueta`, `quitar_etiqueta`, `eliminar_tag` | Asignación idempotente; borrar una etiqueta borra sus asignaciones |
| `motivo_de_rechazo_cv(nombre, contenido)` | Valida el CV antes de subirlo: no vacío, hasta 10 MB, extensión y firma de PDF, y que se pueda abrir. Un PDF escaneado sí se acepta (va a revisión manual). La carga masiva devuelve el motivo de cada archivo fallido |
| Banco de talento | **Implementado (DEV-A-08 · PR #31)** en el router de candidatos, sin servicio aparte: marcar `en_banco_talento` (idempotente) y listar los marcados con filtro por área |

Las métricas del dashboard (DEV-A-10 · PR #29) se calculan en `routers/metricas.py` con consultas de agregación sobre las tablas de la empresa; no tienen servicio aparte.

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
| `encolar_tarea` | Implementado; lo usa `despachar_tarea` en modo `sqs` (PR #42) |

Los clientes de AWS usan el rol de la tarea o de la Lambda. Con credenciales temporales (la Lambda), incluyen el token de sesión (`AWS_SESSION_TOKEN`): sin él, S3 respondía `InvalidAccessKeyId` (hallado en la prueba en AWS del 2026-11-08).

## scripts/ — Implementado

| Script | Tarea | Descripción |
|---|---|---|
| `crear_roles` | DEV-C-11 · PR #10 | Crea `vael_owner`, `vael_app` y `vael_system` (DEC-010) |
| `crear_empresa` | DEV-C-03 · PR #15 (DEC-015) | Crea la empresa y su administrador como `vael_app`, con contraseña temporal enviada por correo. El `tenant_id` es un UUID v5 de la razón social normalizada (`tenant_de`), así no necesita ver otras empresas ni ampliar la lista cerrada. Idempotente |
| `semillas` | DEV-C-03 · PR #15 | Carga los datos del doc 13 (empresas A y B, usuarios por rol, áreas, plantillas, vacantes y los datos de la empresa testigo B). Contraseñas desde `SEED_PASSWORD` o `SEED_PASSWORD_<ROL>`; reutiliza `crear_empresa`. Idempotente. **Ampliado (DEV-A-07 · PR #28):** candidatos de TI-2026-001 con el proceso completo (doc 13 v1.4), sin enviar correos |
| `generar_cvs` | DEV-C-03 · PR #15 | Genera los PDF de los CV ficticios desde `backend/seeds/cvs_texto/`, incluidos el escaneado (CV-TI-11) y el dañado (CV-TI-12) |
| `exportar_openapi` | DEV-C-09 · PR #16 (DEC-008) | Exporta el OpenAPI a `frontend/openapi.json` para generar el cliente tipado |
| `medir_oe2` | TST-A-05 · PR #35 y PR #45; TST-A-06 · PR #48 (en revisión) | Mide el OE2 (doc 14) con llamadas reales al modelo. **`--proveedor gemini\|qwen` (obligatorio, DEC-026):** Gemini sin respaldo, o Qwen directo por `consultar_qwen_json`. Cada proveedor tiene su registro en `docs/metricas/oe2_<proveedor>/` (`consistencia.json`, `intento_NN_<motivo>.json`, `partes/`). Cada ejecución registra proveedor, modelo y, en Qwen, el servidor; nunca la clave. **Por partes (PR #45):** `--cv <código>` y `--unir`, para no superar la cuota diaria |
| `probar_qwen` | DEV-C-15 · PR #44 | Verifica la conexión con Qwen: lista los modelos y hace una consulta de prueba en JSON contra el servidor configurado |

## Consideraciones transversales

- **Idempotencia:** SQS entrega cada mensaje al menos una vez; `aplicar_resultado_*` y el servicio de decisiones no duplican filas, tokens ni correos.
- **Logs:** JSON con `tenant_id`, `candidato_id`, operación y `duration_ms` (DEV-C-08).
- **Cuota de Gemini:** con reintento y backoff (DEV-C-04); en el campus, con `IA_RESPALDO=qwen`, responde Qwen (PR #44); si no, el mensaje vuelve a la cola y, tras los reintentos, termina en la DLQ con alarma.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1 | 2026-09-15 | Versión inicial |
| 2.0 | 2026-10-13 | Alineado con el código real; servicio de decisiones; correo de cierre; brechas |
| 2.1 | 2026-10-18 | División cálculo/aplicación para las Lambdas (DEC-016, DEC-018); despachador; firma HMAC; reintento ante 429 asignado a DEV-C-04; servicios de vacantes y candidatos de la retrospectiva; script de alta de empresa (DEC-015); remitente `vael.work`; referencias a historias de usuario |
| 2.2 | 2026-10-27 | Cierre del Sprint 1: implementados despachador en proceso, `google-genai` con reintento, score, logs JSON, servicio de decisiones, correo de cierre, sesiones, vacantes, candidatos y scripts. Emociones eliminadas. La división cálculo/aplicación y la firma HMAC quedan para HU-23. Pendiente: lote de la etapa entrevista (DEC-022) |
| 2.3 | 2026-11-03 | Sprint 2: recomendación de finalistas por `top_candidatos_finalistas` con `ranking_vacante` y `recomendaciones_finalistas` (DEC-022, PR #27); `enviar_correos=False` para las semillas (PR #28); banco de talento y métricas implementados en sus routers (PR #29, #31); reintento ante 504 y tiempo límite de Gemini (PR #23) |
| 3.0 | 2026-11-04 | **Corrección (versión mayor):** la sección de `services/analisis_cv.py` describía desde la v1 un desglose ponderado que el código no implementaba; DEC-024 lo implementó (DEV-C-14 · PR #38): `construir_prompt_analisis` pide los cinco criterios con su justificación y `_validar_y_sumar_desglose` valida y suma `score_cv` |
| 3.1 | 2026-11-09 | HU-23 integrada (DEV-C-13 · PR #42): despachador con modo `sqs`, `core/interno.py`, y división en preparación, cálculo y aplicación de los análisis de CV y de entrevista pasan a Implementado; Lambda con secreto propio y DLQ; token de sesión en los clientes de AWS |
| 3.2 | 2026-11-10 | Respaldo de IA (DEV-C-15 · PR #44, DEC-025): `consultar_gemini_json` con `permitir_respaldo` y `core/qwen.py`; scripts `medir_oe2` (por partes, PR #45; registros separados de Gemini y Qwen, DEC-026, PR #48 en revisión) y `probar_qwen` agregados a la tabla |
