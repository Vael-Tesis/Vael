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
- **HECHO:** el instituto ofrece a sus estudiantes un modelo Qwen propio, con cuenta y clave de API. **SUPUESTO por verificar:** expone una API compatible con la de OpenAI (`/chat/completions`, `/models`), el formato habitual de los despliegues locales de Qwen. El modelo exacto se descubre con `python -m app.scripts.probar_qwen`.
- En una exposición, un 429 o un 503 de Gemini deja a un candidato sin análisis delante del jurado.

## Decisión

1. **Gemini sigue siendo el proveedor.** Qwen es solo un **respaldo** para las llamadas de texto con salida JSON (`consultar_gemini_json`): análisis de CV, generación y calificación del examen, análisis de la entrevista y textos de la vacante.
2. **Configuración, no código comentado.** Con `IA_RESPALDO=qwen`, si Gemini agota sus reintentos por un error de disponibilidad (429, 503, 504 o tiempo límite), la misma llamada se repite con Qwen de forma automática. Con `IA_PROVEEDOR=qwen`, todas las llamadas van a Qwen. Un error de otro tipo (por ejemplo, una petición inválida) no pasa al respaldo.
3. **La voz no tiene respaldo:** la entrevista con EVA (Gemini Live) sigue dependiendo de Gemini.
4. **La medición del OE2 mide solo a Gemini:** el script la ejecuta con el respaldo desactivado.
5. Cada llamada registra el proveedor y el modelo que respondió.
6. En AWS, la clave de Qwen se guarda en Secrets Manager, en el secreto del backend y en el de la Lambda. La URL, el modelo e `IA_RESPALDO` son parámetros de la pila.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Comentar y descomentar la conexión y el prompt de cada proveedor antes de exponer | Cambia el código fuente justo antes de una demostración. Exige un nuevo despliegue y es fácil equivocarse. Con la variable de entorno, el cambio es de configuración |
| Clave de Gemini de nivel pagado | Descartada por el Product Owner (costo) |
| Cambiar de proveedor por completo | Gemini Live (voz) no tiene equivalente en Qwen, y el OE2 se definió sobre Gemini |

## Trade-off aceptado

- **Resultados distintos según el modelo:** un análisis hecho por Qwen puede puntuar distinto que uno de Gemini. Los registros muestran qué proveedor respondió. Los resultados del OE2 siguen siendo solo de Gemini.
- **Datos personales en otro servidor:** los CV enviados al respaldo salen hacia el servidor del instituto. En las exposiciones se usan los datos semilla ficticios (doc 13). Para usarlo con datos reales, habría que revisarlo frente a la Ley 29733 de protección de datos personales.
- **SUPUESTO por verificar: alcance de red.** Si el servidor del instituto solo es accesible desde la red del campus, el backend y la Lambda en AWS no llegan a él. En ese caso, el respaldo solo sirve con el sistema en local.

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
- Prueba manual: `python -m app.scripts.probar_qwen` lista los modelos y obtiene un JSON válido.
- Prueba en AWS, si el servidor es accesible desde internet: con `IA_PROVEEDOR=qwen`, un CV cargado obtiene su recomendación.
