# DEC-025 — Qwen del instituto como IA de respaldo de Gemini

| Campo | Valor |
|---|---|
| Estado | Propuesta |
| Fecha | 2026-11-08 |
| Tarea de origen | DEV-C-15 (pedido del Product Owner para las exposiciones) |
| Propuesto por | Gabriel Llanos (Product Owner); registrada por Gabriel Llanos |
| Relacionada con | DEC-016 y DEC-018 (procesamiento asíncrono), OE2 (doc 14); doc 04 (stack) |

## Contexto

- **HECHO:** la cuenta de Gemini del proyecto usa el plan gratuito. Ese plan permite 20 solicitudes por día y por modelo (doc 04). La primera corrida del OE2 falló en las 30 ejecuciones por la cuota y por la alta demanda (PR #35), y el primer despliegue en AWS no completó un análisis porque Google respondía 503 (doc 09).
- **HECHO:** el Product Owner decidió no pagar una clave de nivel pagado.
- **HECHO:** el instituto ofrece a sus estudiantes un modelo Qwen propio en un Open WebUI, con cuenta y clave de API compatible con la de OpenAI (`/api/chat/completions`, `/api/models`). El modelo es `Qwen/Qwen3.6-35B-A3B-FP8` (código de un proyecto anterior del Product Owner).
- **HECHO:** el servidor está en una **IP privada de la red de Tecsup**. Solo es alcanzable desde el campus; desde fuera, o desde AWS, no responde.
- En una exposición, un 429 o un 503 de Gemini deja a un candidato sin análisis delante del jurado. Las exposiciones son en Tecsup, con VAEL corriendo en local.

## Decisión

1. **Gemini sigue siendo el proveedor.** Qwen es solo un **respaldo** para las llamadas de texto con salida JSON (`consultar_gemini_json`): análisis de CV, generación y calificación del examen, análisis de la entrevista y textos de la vacante.
2. **Configuración, no código comentado.** Con `IA_RESPALDO=qwen`, si Gemini agota sus reintentos por un error de disponibilidad (429, 503, 504 o tiempo límite), la misma llamada se repite con Qwen de forma automática. Con `IA_PROVEEDOR=qwen`, todas las llamadas van a Qwen. Un error de otro tipo (por ejemplo, una petición inválida) no pasa al respaldo.
3. **La voz no tiene respaldo:** la entrevista con EVA (Gemini Live) sigue dependiendo de Gemini.
4. **La medición del OE2 mide solo a Gemini:** el script la ejecuta con el respaldo desactivado.
5. Cada llamada registra el proveedor y el modelo que respondió.
6. **Uso previsto: local, en la red de Tecsup.** La configuración vive en `backend/.env`, fuera de Git. En AWS el respaldo queda desactivado salvo que se encienda con `aws-encender.ps1 -ConQwen`. Así, cada falla de Gemini no espera a un servidor que la nube no alcanza. Si en algún momento el servidor fuera público, la pila ya acepta su URL, su modelo y su clave (esta última, en Secrets Manager).

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Comentar y descomentar la conexión y el prompt de cada proveedor antes de exponer | Cambia el código fuente justo antes de una demostración. Exige un nuevo despliegue y es fácil equivocarse. Con la variable de entorno, el cambio es de configuración |
| Clave de Gemini de nivel pagado | Descartada por el Product Owner (costo) |
| Cambiar de proveedor por completo | Gemini Live (voz) no tiene equivalente en Qwen, y el OE2 se definió sobre Gemini |

## Trade-off aceptado

- **Resultados distintos según el modelo:** un análisis hecho por Qwen puede puntuar distinto que uno de Gemini. Los registros muestran qué proveedor respondió. Los resultados del OE2 siguen siendo solo de Gemini.
- **Datos personales en otro servidor:** los CV enviados al respaldo salen hacia el servidor del instituto. En las exposiciones se usan los datos semilla ficticios (doc 13). Para usarlo con datos reales, habría que revisarlo frente a la Ley 29733 de protección de datos personales.
- **Solo en el campus:** fuera de la red de Tecsup, y en AWS, no hay respaldo. Las demos en `app.vael.work` siguen dependiendo de la cuota de Gemini.
- **Modelo de razonamiento:** Qwen3 puede anteponer su razonamiento entre `<think>` y `</think>`. El cliente lo quita antes de leer el JSON.

## Consecuencias

| Elemento | Cambio |
|---|---|
| `core/qwen.py`, `core/gemini.py`, `core/config.py` | Cliente de Qwen y respaldo automático |
| `app/scripts/probar_qwen.py` | Descubre el modelo y prueba la conexión |
| `app/scripts/medir_oe2.py` | Respaldo desactivado |
| `infra/aws/entorno.yaml`, `scripts/aws-encender.ps1` | Parámetros de Qwen y su clave en Secrets Manager |
| Docs 04, 08 y 09 | Proveedor de respaldo, variables y configuración |
| `CLAUDE.md`, sección 5 | Gemini como proveedor, con Qwen como respaldo |

## Validación

- Test: con `IA_RESPALDO=qwen`, un 429 de Gemini produce la respuesta de Qwen.
- Test: sin respaldo configurado, o con un error que no es de disponibilidad, el error de Gemini se propaga.
- Test: con `permitir_respaldo=False` (OE2), no se usa Qwen.
- Test: la respuesta se lee aunque traiga razonamiento, un bloque de markdown o texto alrededor del JSON.
- Prueba manual en la red de Tecsup: `python -m app.scripts.probar_qwen` lista los modelos y obtiene un JSON válido. Luego, con `IA_PROVEEDOR=qwen`, un CV cargado en local obtiene su recomendación.
