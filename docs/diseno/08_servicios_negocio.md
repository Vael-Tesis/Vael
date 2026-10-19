> COPIA del documento del Drive `VAEL/Docs/08_servicios_negocio.md`, versión 2.1, copiada el 2026-10-18.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 08 — Servicios de Negocio

| Campo | Valor |
|---|---|
| Versión | 2.1 |
| Actualizado | 2026-10-18 |
| Fuente de verdad | Código en `backend/app/services/` y `backend/app/core/` (revisado el 2026-10-13) + DEC-001, DEC-002, DEC-007, DEC-009, DEC-010, DEC-013, DEC-015, DEC-016, DEC-018 |
| Copia en el repositorio | `docs/diseno/08_servicios_negocio.md` (DEC-019). La fuente es este documento |

Los servicios contienen la lógica de negocio y no dependen de FastAPI. Estados: **Implementado** · **Cambia (tarea · historia)** · **Planificado (tarea · historia)** · **Se elimina (tarea)**.

## Reglas transversales

1. **La IA recomienda; nunca decide (DEC-009).** Ningún servicio de análisis cambia a un estado de avance o descarte, emite tokens ni envía correos al candidato. Eso solo lo hace el servicio de decisiones.
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

## core/despacho.py — Planificado (DEV-C-13 · HU-21 y HU-23)

| Función | Descripción |
|---|---|
| `despachar_tarea(tipo, payload)` | En producción publica en la cola SQS del `tipo`; en desarrollo y tests ejecuta `calcular_*` y `aplicar_resultado_*` en el mismo proceso |

Colas: `vael-analisis-cv` y `vael-analisis-entrevista`, cada una con su DLQ (cola de mensajes fallidos).

## core/gemini.py — Implementado (cambia en DEV-C-04 · HU-21)

| Función | Descripción |
|---|---|
| `consultar_gemini_json(prompt, model_name=None)` | Llama a Gemini pidiendo JSON y lo parsea |
| `como_lista_str(valor)` | Normaliza listas devueltas por el modelo |

**Cambia (DEV-C-04):** pasa de `google-generativeai` (deprecado) a `google-genai`, verifica el ID de modelo, registra el modelo y los parámetros de cada llamada (OE2) e **incorpora reintento con backoff exponencial ante el error 429** (hoy no existe).

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
| `construir_prompt_analisis(texto_cv, datos_vacante)` | Implementado. **Cambia (DEV-C-13):** recibe los datos de la vacante como diccionario, no como objeto de la base de datos | Texto del CV, requisitos, habilidades, tecnologías, nivel, instrucciones de IA; exige JSON puro |
| `calcular_analisis_cv(mensaje)` | **Planificado (DEV-C-13)** | Parte de cálculo: descarga el PDF, extrae el texto, llama a Gemini y devuelve el resultado. Sin base de datos |
| `aplicar_resultado_analisis_cv(resultado, tenant_id)` | **Planificado (DEV-C-10/13)** | Guarda score, clasificación, resumen, habilidades, inconsistencias y enlaces; genera la recomendación según `score_cv_minimo`; deja `cv_por_confirmar`. No emite tokens ni envía correos |
| `analizar_cv(...)` y `analizar_cv_candidato(...)` | Implementados hoy | **Se reemplazan** por las dos funciones anteriores |

Criterios del score (0-100): match de habilidades (0-40), experiencia (0-20), formación (0-15), coherencia (0-15), trayectoria (0-10). Respuesta esperada: doc 07, etapa 3.

## services/examen.py

| Función | Estado | Descripción |
|---|---|---|
| `generar_preguntas(...)` | Implementado | 6 de opción múltiple y 4 abiertas sobre la intersección CV–vacante |
| `calificar_examen(examen_id, db)` | **Cambia (DEV-C-10)** | Opción múltiple 2/0; abiertas 0/1/2 con Gemini; nota sobre 20; semáforo; genera la recomendación y deja `examen_por_confirmar` |
| `registrar_evento(...)` | Implementado | Crea el evento y suma el puntaje de riesgo |

## services/entrevista_ia.py

| Función | Estado | Descripción |
|---|---|---|
| `generar_token_efimero_live()` | Implementado | `expireTime` 30 min; `newSessionExpireTime` 10 min |
| `generar_pool_preguntas(...)` | Implementado | 8 a 12 preguntas con prioridad |
| `construir_system_instruction(...)` | Implementado. **Cambia (DEV-B-11, ciclo siguiente):** del voseo al español neutro | Comportamiento de EVA |
| `analizar_entrevista(...)` | Implementado. **Cambia (DEV-C-13 · HU-23):** se divide en `calcular_analisis_entrevista` (Lambda) y `aplicar_resultado_analisis_entrevista` (backend). **Cambia (DEV-C-01):** `score_final` con DEC-007 | Nota por dimensión con justificación; deja `entrevista_realizada` |

## services/decisiones.py — Planificado (DEV-C-10 · HU-15, HU-16, HU-18)

Único servicio autorizado a ejecutar avances y descartes.

| Función | Descripción |
|---|---|
| `registrar_decision(...)` | Valida la recomendación pendiente, exige justificación si no coincide, inserta en `decisiones_candidato` y ejecuta el efecto |
| `registrar_decisiones_lote(...)` | Solo decisiones que coinciden con la recomendación |
| `revertir_decision(...)` | Inserta una decisión nueva con `reemplaza_a` |

| Etapa | Avanzar | Descartar |
|---|---|---|
| `cv` | `cv_aprobado` + token + `correo_bienvenida_examen` | `cv_rechazado` + `correo_cierre_proceso` |
| `examen` | `examen_aprobado` + token + `correo_invitacion_entrevista` | `examen_rechazado` + `correo_cierre_proceso` |
| `entrevista` | `finalista` + `correo_finalista` | `descartado` + `correo_cierre_proceso` |

## services/correos.py

| Función | Estado |
|---|---|
| `correo_bienvenida_examen`, `correo_invitacion_entrevista`, `correo_finalista`, `correo_credenciales_usuario` | Implementados |
| `correo_cierre_proceso(candidato, vacante)` | **Planificado (DEV-C-10 · HU-15, DEC-013):** agradecimiento, cierre del proceso, uso de IA con revisión humana, contacto para datos personales; sin puntajes ni razones |

Guarda de envío: hoy bloquea todo correo a candidatos rechazados o descartados. **Con DEC-013:** a un descartado solo se le envía `correo_cierre_proceso`, una vez por vacante. Remitente en producción: `noreply@vael.work` (DEC-018).

## services/vacantes.py — Planificado (DEV-A-04 · HU-08, HU-10)

| Función | Descripción |
|---|---|
| `eliminar_vacante(id)` | Solo en estado `borrador`; 409 en otro caso |
| `guardar_textos_publicacion(id, textos)` | Persiste `textos_publicacion` |

`services/vacante_ia.py` — `generar_textos_marketing(vacante)` — Implementado.

## services/candidatos.py — Planificado (DEV-A-01, DEV-A-08 · HU-13, HU-14)

Edición y eliminación de notas (solo el autor edita; autor o admin eliminan; actualiza `updated_at`), asignación idempotente de etiquetas y marca de banco de talento.

## services/aws_services.py

| Función | Estado |
|---|---|
| `validar_identidad`, `detectar_segunda_persona` | Implementados (verificación de presencia; ciclo siguiente) |
| `detectar_emociones`, `analizar_sentimiento` | **Se eliminan (DEV-C-12 · HU-21, DEC-001)** |
| `transcribir_audio` | Implementado, sin uso (se decide en el ciclo siguiente) |
| `subir_archivo`, `descargar_archivo`, `generar_url_prefirmada` | Implementados (S3; URLs de 1 hora) |
| `enviar_correo` | Implementado (SES) |
| `encolar_tarea` | Implementado, sin uso. Lo usará `despachar_tarea` en producción |

## scripts/crear_empresa.py — Planificado (DEV-C-03 · HU-21, DEC-015)

Crea la empresa con su `tenant_id`, fija ese tenant, crea al administrador inicial con contraseña temporal y le envía las credenciales. Idempotente. Lo reutiliza el script de semillas.

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
