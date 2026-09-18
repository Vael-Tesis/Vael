"""Servicios de AWS: Rekognition, Transcribe, Comprehend, S3, SES y SQS — todo vía aioboto3."""
import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

import aioboto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def _cliente(servicio: str, region_name: str | None = None) -> Any:
    """Crea un cliente async de un servicio de AWS vía aioboto3 (usar con `async with`).

    Si no hay credenciales estáticas en settings (caso típico en producción, donde ECS
    Fargate usa el IAM task role en vez de access keys), se pasan como None para que
    aioboto3 caiga en la cadena de credenciales por defecto, en vez de mandar strings vacíos.
    """
    sesion = aioboto3.Session(
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        region_name=region_name or settings.aws_region,
    )
    return sesion.client(servicio)


# --- Rekognition ----------------------------------------------------------


async def detectar_emociones(imagen_bytes: bytes) -> dict[str, float]:
    """Detecta las 8 emociones de Rekognition en el primer rostro de la imagen (confianza 0-100)."""
    async with _cliente("rekognition") as rekognition:
        respuesta = await rekognition.detect_faces(Image={"Bytes": imagen_bytes}, Attributes=["ALL"])

    rostros = respuesta.get("FaceDetails", [])
    if not rostros:
        return {}

    return {emocion["Type"].lower(): emocion["Confidence"] for emocion in rostros[0].get("Emotions", [])}


async def validar_identidad(imagen_bytes: bytes) -> bool:
    """Valida que la imagen tenga exactamente un rostro visible (identidad antes del examen)."""
    async with _cliente("rekognition") as rekognition:
        respuesta = await rekognition.detect_faces(Image={"Bytes": imagen_bytes}, Attributes=["DEFAULT"])

    return len(respuesta.get("FaceDetails", [])) == 1


async def detectar_segunda_persona(imagen_bytes: bytes) -> bool:
    """Detecta más de un rostro en la imagen — indicio de una segunda persona en cámara.

    Alimenta el evento de proctoring "segunda_persona" del catálogo de la sección 11.
    """
    async with _cliente("rekognition") as rekognition:
        respuesta = await rekognition.detect_faces(Image={"Bytes": imagen_bytes}, Attributes=["DEFAULT"])

    return len(respuesta.get("FaceDetails", [])) > 1


# --- Transcribe -------------------------------------------------------------


async def _descargar_y_formatear_transcripcion(uri_resultado: str) -> str:
    """Descarga el resultado JSON de un job de Transcribe y arma el texto con diarización."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        respuesta = await client.get(uri_resultado)
        respuesta.raise_for_status()
        resultado = respuesta.json()

    items = resultado.get("results", {}).get("items", [])
    segmentos = resultado.get("results", {}).get("speaker_labels", {}).get("segments", [])

    hablante_por_inicio: dict[str, str] = {
        item_segmento["start_time"]: segmento["speaker_label"]
        for segmento in segmentos
        for item_segmento in segmento.get("items", [])
    }

    lineas: list[str] = []
    hablante_actual: str | None = None
    palabras_actuales: list[str] = []

    for item in items:
        contenido = item["alternatives"][0]["content"]

        if item["type"] == "punctuation":
            if palabras_actuales:
                palabras_actuales[-1] += contenido
            continue

        hablante = hablante_por_inicio.get(item.get("start_time"), hablante_actual or "spk_0")

        if hablante != hablante_actual:
            if palabras_actuales:
                lineas.append(f"{hablante_actual}: {' '.join(palabras_actuales)}")
            hablante_actual = hablante
            palabras_actuales = [contenido]
        else:
            palabras_actuales.append(contenido)

    if palabras_actuales:
        lineas.append(f"{hablante_actual}: {' '.join(palabras_actuales)}")

    return "\n".join(lineas)


async def transcribir_audio(audio_url: str, idioma: str = "es-ES", max_espera_segundos: int = 300) -> str:
    """Transcribe un audio con diarización (quién habla) usando AWS Transcribe.

    Transcribe es un servicio asíncrono por naturaleza en AWS (se lanza un job y hay que
    consultarlo hasta que termine) — esta función hace ese polling internamente, así que
    puede tardar minutos. Está pensada para correr dentro de un background task, no en el
    ciclo de un request HTTP.
    """
    nombre_job = f"vael-transcribe-{uuid4().hex}"

    async with _cliente("transcribe") as transcribe:
        await transcribe.start_transcription_job(
            TranscriptionJobName=nombre_job,
            Media={"MediaFileUri": audio_url},
            LanguageCode=idioma,
            Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 4},
        )

        transcurrido = 0
        intervalo = 5
        while transcurrido < max_espera_segundos:
            estado = await transcribe.get_transcription_job(TranscriptionJobName=nombre_job)
            job = estado["TranscriptionJob"]
            job_estado = job["TranscriptionJobStatus"]

            if job_estado == "COMPLETED":
                return await _descargar_y_formatear_transcripcion(job["Transcript"]["TranscriptFileUri"])
            if job_estado == "FAILED":
                raise RuntimeError(f"El job de Transcribe {nombre_job} falló: {job.get('FailureReason')}")

            await asyncio.sleep(intervalo)
            transcurrido += intervalo

    raise TimeoutError(f"Transcribe no terminó el job {nombre_job} en {max_espera_segundos}s")


# --- Comprehend ---------------------------------------------------------


async def analizar_sentimiento(texto: str) -> dict[str, float]:
    """Analiza el sentimiento de un texto con Comprehend — retorna los 4 scores (0-1)."""
    async with _cliente("comprehend") as comprehend:
        # DetectSentiment acepta hasta 5000 bytes UTF-8; se trunca de forma defensiva.
        respuesta = await comprehend.detect_sentiment(Text=texto[:5000], LanguageCode="es")

    scores = respuesta.get("SentimentScore", {})
    return {
        "positivo": scores.get("Positive", 0.0),
        "negativo": scores.get("Negative", 0.0),
        "neutral": scores.get("Neutral", 0.0),
        "mixto": scores.get("Mixed", 0.0),
    }


# --- S3 -------------------------------------------------------------------


async def subir_archivo(archivo_bytes: bytes, key: str, content_type: str) -> str:
    """Sube un archivo a S3 y retorna su URL."""
    async with _cliente("s3") as s3:
        await s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=archivo_bytes,
            ContentType=content_type,
        )

    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"


async def descargar_archivo(key: str) -> bytes:
    """Descarga un archivo de S3 por su key."""
    async with _cliente("s3") as s3:
        respuesta = await s3.get_object(Bucket=settings.s3_bucket_name, Key=key)
        async with respuesta["Body"] as cuerpo:
            return await cuerpo.read()


async def generar_url_prefirmada(key: str, expires: int = 3600) -> str:
    """Genera una URL prefirmada de S3, válida por `expires` segundos (default 1 hora).

    NOTA: a diferencia de boto3 (donde generate_presigned_url es síncrono, solo firma
    localmente), en aiobotocore queda expuesto como awaitable porque el cliente puede
    necesitar resolver credenciales de forma async — es un detalle que ha cambiado entre
    versiones de aiobotocore, conviene confirmarlo contra la que quede instalada.
    """
    async with _cliente("s3") as s3:
        return await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": key},
            ExpiresIn=expires,
        )


# --- SES --------------------------------------------------------------


async def enviar_correo(to: str, subject: str, html_body: str, from_email: str) -> bool:
    """Envía un correo por AWS SES. Retorna True si SES aceptó el envío, False si falló.

    Función de bajo nivel — services/correos.py arma el asunto/HTML de cada plantilla y
    decide cuándo usar SES (producción) vs. SMTP local (desarrollo); esta función solo
    sabe hablar con SES.
    """
    try:
        async with _cliente("ses", region_name=settings.ses_region) as ses:
            await ses.send_email(
                Source=from_email,
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
        return True
    except (BotoCoreError, ClientError):
        logger.exception("Falló el envío de correo por SES a %s", to)
        return False


# --- SQS --------------------------------------------------------------


async def encolar_tarea(cola_url: str, payload: dict[str, Any], delay_segundos: int = 0) -> str:
    """Encola un mensaje en SQS (p. ej. para que lo procese una Lambda async). Retorna el MessageId."""
    async with _cliente("sqs") as sqs:
        respuesta = await sqs.send_message(
            QueueUrl=cola_url,
            MessageBody=json.dumps(payload),
            DelaySeconds=delay_segundos,
        )

    return respuesta["MessageId"]
