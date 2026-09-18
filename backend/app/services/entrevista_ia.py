"""Servicio de entrevista conversacional con EVA sobre Gemini Live API."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from google import genai
from google.genai import types
from sqlmodel import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.gemini import consultar_gemini_json
from app.models.base import utcnow
from app.models.candidato import Candidato, EstadoCandidato
from app.models.entrevista import DimensionEvaluacion, EntrevistaIA, PlantillaEvaluacion
from app.models.evaluacion import Examen
from app.models.vacante import Vacante

logger = logging.getLogger(__name__)

_PRIORIDADES_VALIDAS = ("critica", "alta", "media")


def construir_system_instruction(
    candidato: Candidato,
    vacante: Vacante | None,
    pool_preguntas: list[dict[str, str]],
) -> str:
    """Arma la instrucción de sistema de EVA para la sesión de Gemini Live de esta entrevista."""
    titulo = vacante.titulo if vacante else "la vacante"
    preguntas_texto = "\n".join(
        f"- [{p.get('prioridad', 'media')}] {p.get('enunciado', '')}" for p in pool_preguntas
    )

    return f"""
Eres EVA, la entrevistadora de IA de VAEL. Estás entrevistando por voz a {candidato.nombre} para
la vacante "{titulo}".

## Tu personalidad
Profesional, cálida y cercana. Hablás en español neutro, con oraciones cortas y naturales
(esto es una conversación de voz, no un texto para leer). Escuchás activamente y hacés
preguntas de seguimiento cuando la respuesta lo amerita.

## Pool de preguntas (prioridad entre corchetes)
{preguntas_texto}

## Reglas de la entrevista
1. Empezá con una bienvenida breve y explicá que la entrevista dura unos 20 minutos.
2. Recorré las preguntas en el orden que consideres natural según la conversación, no
   necesariamente en el orden listado.
3. Si quedan menos de 5 minutos y todavía hay preguntas marcadas como [critica] sin hacer,
   adelantalas de inmediato, sin esperar una transición natural — son las que más pesan en
   la evaluación final.
4. No reveles nunca que estás evaluando ni des retroalimentación sobre qué tan bien respondió
   el candidato.
5. Cerrá la entrevista agradeciendo su tiempo y explicando que va a recibir noticias por correo.
""".strip()


async def generar_token_efimero_live(
    candidato: Candidato,
    vacante: Vacante | None,
    pool_preguntas: list[dict[str, str]],
) -> str:
    """Emite un token efímero de la API de Gemini Live para que el frontend abra el WebSocket.

    Válido 30 minutos, con 10 minutos de margen para iniciar la sesión (new_session_expire_time),
    tal como pide la sección 10 del CLAUDE.md. El system_instruction de EVA queda embebido en
    las restricciones del token (live_connect_constraints) para que el frontend no pueda alterarlo.

    NOTA: los tokens efímeros de Gemini Live son del SDK google-genai (client.aio.auth_tokens),
    no del SDK google-generativeai que usan los demás servicios — requiere google-genai>=2.24.0
    (la versión con la que se pineó al principio, 0.2.2, es anterior a que existiera esta
    función). Los nombres de client.aio.auth_tokens.create, CreateAuthTokenConfig,
    LiveConnectConstraints y sus campos (uses, expire_time, new_session_expire_time,
    live_connect_constraints, model, config) están verificados contra el paquete real
    instalado — lo que no se pudo probar en este entorno es una llamada real a la API de
    Google (necesita una API key válida), así que la superficie del SDK es correcta pero
    el comportamiento en runtime contra Gemini Live todavía no está confirmado.
    """
    system_instruction = construir_system_instruction(candidato, vacante, pool_preguntas)

    cliente = genai.Client(api_key=settings.gemini_api_key, http_options={"api_version": "v1alpha"})
    ahora = datetime.now(timezone.utc)

    token = await cliente.aio.auth_tokens.create(
        config=types.CreateAuthTokenConfig(
            uses=1,
            expire_time=ahora + timedelta(minutes=30),
            new_session_expire_time=ahora + timedelta(minutes=10),
            live_connect_constraints=types.LiveConnectConstraints(
                model=settings.gemini_live_model,
                config=types.LiveConnectConfig(
                    response_modalities=[types.Modality.AUDIO],
                    system_instruction=system_instruction,
                ),
            ),
        ),
    )

    return token.name


def _construir_prompt_pool_preguntas(
    candidato: Candidato,
    vacante: Vacante | None,
    plantilla: PlantillaEvaluacion | None,
) -> str:
    """Arma el prompt de generación del pool dinámico de preguntas de la entrevista."""
    titulo = vacante.titulo if vacante else "la vacante"
    requisitos = (
        vacante.requisitos if vacante and vacante.requisitos else "No se especificaron requisitos obligatorios."
    )
    resumen_cv = candidato.resumen_ia or "No hay un resumen de CV disponible."
    habilidades_cv = (
        ", ".join(candidato.habilidades_detectadas) if candidato.habilidades_detectadas else "No detectadas."
    )
    plantilla_nombre = plantilla.nombre if plantilla else "evaluación general"

    return f"""
Eres un entrevistador técnico armando el guion de preguntas para una entrevista de voz.

## Vacante: {titulo}
Requisitos: {requisitos}

## Perfil del candidato (según el análisis de su CV)
Resumen: {resumen_cv}
Habilidades detectadas: {habilidades_cv}

## Plantilla de evaluación
{plantilla_nombre}

## Tarea
Genera entre 8 y 12 preguntas para la entrevista, cada una con una prioridad: "critica"
(imprescindible tocarla), "alta" o "media". Responde ÚNICAMENTE con un JSON (sin texto
adicional, sin markdown):

{{
  "preguntas": [
    {{"enunciado": "<pregunta>", "prioridad": "<critica|alta|media>"}}
  ]
}}
""".strip()


async def generar_pool_preguntas(
    candidato: Candidato,
    vacante: Vacante | None,
    plantilla: PlantillaEvaluacion | None,
) -> list[dict[str, str]]:
    """Genera con Gemini el pool dinámico de 8-12 preguntas de la entrevista, cada una con su
    prioridad (crítica|alta|media) — sección 10 del CLAUDE.md.

    El adelanto de las preguntas críticas cuando quedan menos de 5 minutos lo maneja EVA en
    vivo (ver construir_system_instruction) — esta función solo genera el pool una vez, al
    iniciar la entrevista.
    """
    prompt = _construir_prompt_pool_preguntas(candidato, vacante, plantilla)
    resultado = await consultar_gemini_json(prompt)

    preguntas: list[dict[str, str]] = []
    for item in resultado.get("preguntas", []):
        prioridad = str(item.get("prioridad", "media")).lower()
        if prioridad not in _PRIORIDADES_VALIDAS:
            prioridad = "media"
        preguntas.append({"enunciado": str(item.get("enunciado", "")), "prioridad": prioridad})

    return preguntas


def _construir_prompt_analisis_entrevista(transcripcion: str, dimensiones: list[DimensionEvaluacion]) -> str:
    """Arma el prompt de análisis multidimensional de la entrevista."""
    dimensiones_texto = "\n".join(
        f"- {d.nombre} (máximo {d.puntaje_maximo} pts, peso {d.peso}): {d.descripcion or 'sin descripción'}"
        for d in dimensiones
    )

    return f"""
Eres un evaluador experto de entrevistas de trabajo. Analiza la siguiente transcripción de
una entrevista conversacional y califica al candidato en cada una de las dimensiones dadas.

## Dimensiones a evaluar
{dimensiones_texto}

## Transcripción de la entrevista
{transcripcion}

## Tarea
Para cada dimensión, en el mismo orden en que se listaron, asigná una nota entre 0 y su
puntaje máximo, con un comentario breve que la justifique. Responde ÚNICAMENTE con un JSON
(sin texto adicional, sin markdown):

{{
  "dimensiones": [
    {{"nota": <número>, "comentario": "<justificación breve>"}}
  ]
}}
""".strip()


def _como_nota_dimension(valor: Any, puntaje_maximo: float) -> float:
    """Normaliza la nota de una dimensión, acotada entre 0 y su puntaje máximo."""
    try:
        nota = float(valor)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(puntaje_maximo, nota))


async def analizar_entrevista(
    transcripcion: str,
    dimensiones: list[DimensionEvaluacion],
) -> tuple[dict[str, Any], float]:
    """Evalúa la transcripción de una entrevista con Gemini contra las dimensiones de la plantilla.

    Retorna (dimensiones_json, nota_final). nota_final es el promedio ponderado por el peso de
    cada dimensión (cada nota se normaliza primero a 0-1 sobre su propio puntaje_maximo, para
    que dimensiones con escalas distintas pesen de forma comparable), escalado a 0-20.
    """
    if not dimensiones:
        return {}, 0.0

    prompt = _construir_prompt_analisis_entrevista(transcripcion, dimensiones)
    resultado = await consultar_gemini_json(prompt)
    calificaciones = resultado.get("dimensiones", [])

    dimensiones_json: dict[str, Any] = {}
    suma_ponderada = 0.0
    suma_pesos = 0.0

    for indice, dimension in enumerate(dimensiones):
        item = calificaciones[indice] if indice < len(calificaciones) else {}
        nota_dimension = _como_nota_dimension(item.get("nota"), dimension.puntaje_maximo)

        dimensiones_json[dimension.nombre] = {
            "nota": nota_dimension,
            "puntaje_maximo": dimension.puntaje_maximo,
            "peso": dimension.peso,
            "comentario": str(item.get("comentario") or ""),
        }

        if dimension.puntaje_maximo > 0:
            suma_ponderada += (nota_dimension / dimension.puntaje_maximo) * dimension.peso
            suma_pesos += dimension.peso

    nota_final = round((suma_ponderada / suma_pesos) * 20, 2) if suma_pesos > 0 else 0.0

    return dimensiones_json, nota_final


async def analizar_entrevista_candidato(entrevista_id: str) -> None:
    """Punto de entrada para background tasks: analiza la entrevista finalizada, guarda su nota
    y dimensiones, y calcula el score_final del candidato (sección 7 del CLAUDE.md).

    Abre su propia sesión de BD porque corre después de que la sesión del request original
    ya se cerró.
    """
    async with async_session_factory() as db:
        entrevista = await db.get(EntrevistaIA, entrevista_id)
        if entrevista is None or not entrevista.transcripcion:
            return

        dimensiones: list[DimensionEvaluacion] = []
        if entrevista.plantilla_id:
            statement = select(DimensionEvaluacion).where(
                DimensionEvaluacion.plantilla_id == entrevista.plantilla_id
            )
            result = await db.exec(statement)
            dimensiones = list(result.all())

        try:
            dimensiones_json, nota_entrevista = await analizar_entrevista(entrevista.transcripcion, dimensiones)
        except Exception:
            logger.exception("Falló el análisis de la entrevista %s", entrevista_id)
            return

        entrevista.nota = nota_entrevista
        entrevista.dimensiones_json = dimensiones_json
        db.add(entrevista)
        await db.commit()

        candidato = await db.get(Candidato, entrevista.candidato_id)
        if candidato is None:
            return

        examen_statement = select(Examen).where(
            Examen.candidato_id == candidato.id,
            Examen.vacante_id == candidato.vacante_id,
        )
        examen_result = await db.exec(examen_statement)
        examen = examen_result.first()

        # Score Final = CV×0.25 + Examen×0.40 + Entrevista×0.35 (sección 7) — la fórmula no
        # normaliza escalas (score_cv es sobre 100, las notas de examen/entrevista sobre 20),
        # así que el resultado no queda en 0-100 ni 0-20 limpio; solo sirve para el orden
        # relativo del ranking (GET /candidatos/ranking), no como puntaje absoluto.
        if candidato.score_cv is not None and examen is not None and examen.nota is not None:
            candidato.score_final = round(
                candidato.score_cv * 0.25 + examen.nota * 0.40 + nota_entrevista * 0.35,
                2,
            )

        candidato.estado = EstadoCandidato.ENTREVISTA_REALIZADA
        candidato.updated_at = utcnow()
        db.add(candidato)
        await db.commit()
