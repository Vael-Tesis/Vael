"""Servicio de generación y calificación de exámenes técnicos con Gemini."""
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.gemini import consultar_gemini_json
from app.core.proctoring import CATALOGO_EVENTOS_PROCTORING, EVENTO_DEFAULT, calcular_semaforo
from app.core.security import emitir_token_candidato
from app.models.area import Area
from app.models.base import utcnow
from app.models.candidato import Candidato, EstadoCandidato
from app.models.evaluacion import Examen, EventoAuditoria, PreguntaExamen, TipoPregunta
from app.models.usuario import TipoToken
from app.models.vacante import Vacante
from app.services.correos import correo_invitacion_entrevista

# Re-exportado para que app.services.examen.calcular_semaforo también sea válido —
# la implementación real vive en core/proctoring.py, compartida con entrevista.
__all__ = ["generar_preguntas", "calificar_examen", "registrar_evento", "calcular_semaforo"]


def _como_tipo_pregunta(valor: Any) -> TipoPregunta:
    """Normaliza el tipo de pregunta devuelto por Gemini; si es inesperado, cae a 'abierta'."""
    try:
        return TipoPregunta(valor)
    except ValueError:
        return TipoPregunta.ABIERTA


def _como_lista_opciones(valor: Any) -> list[str]:
    """Normaliza las opciones de una pregunta MC a list[str]."""
    if not isinstance(valor, list):
        return []
    return [str(item) for item in valor if isinstance(item, str)]


def _construir_prompt_preguntas(candidato: Candidato, vacante: Vacante | None, area: Area | None) -> str:
    """Arma el prompt de generación del examen: 6 preguntas MC + 4 abiertas."""
    titulo = vacante.titulo if vacante else "la vacante"
    requisitos = (
        vacante.requisitos if vacante and vacante.requisitos else "No se especificaron requisitos obligatorios."
    )
    tecnologias = ", ".join(vacante.tecnologias) if vacante and vacante.tecnologias else "No especificadas."
    nivel = vacante.nivel_experiencia.value if vacante and vacante.nivel_experiencia else "no especificado"
    instruccion_area = (
        area.instruccion_ia if area and area.instruccion_ia else "Sin instrucciones adicionales del área."
    )
    resumen_cv = candidato.resumen_ia or "No hay un resumen de CV disponible."
    habilidades_cv = (
        ", ".join(candidato.habilidades_detectadas) if candidato.habilidades_detectadas else "No detectadas."
    )

    return f"""
Eres un examinador técnico. Genera un examen de 10 preguntas para evaluar a un candidato a
la vacante "{titulo}" (nivel: {nivel}).

## Requisitos de la vacante
{requisitos}
Tecnologías: {tecnologias}

## Instrucción específica del área
{instruccion_area}

## Perfil del candidato (según el análisis de su CV)
Resumen: {resumen_cv}
Habilidades detectadas: {habilidades_cv}

## Tarea
Genera exactamente 10 preguntas: las primeras 6 de opción múltiple (4 opciones cada una, con
exactamente una correcta) y las últimas 4 abiertas. Responde ÚNICAMENTE con un JSON (sin texto
adicional, sin bloques de markdown) con esta forma:

{{
  "preguntas": [
    {{
      "tipo": "multiple_choice",
      "enunciado": "<pregunta>",
      "opciones": ["<opcion1>", "<opcion2>", "<opcion3>", "<opcion4>"],
      "respuesta_correcta": "<una de las 4 opciones, tal cual>"
    }},
    {{
      "tipo": "abierta",
      "enunciado": "<pregunta abierta>"
    }}
  ]
}}
""".strip()


async def generar_preguntas(candidato: Candidato, vacante: Vacante | None, area: Area | None) -> list[PreguntaExamen]:
    """Genera 10 preguntas de examen con Gemini: 6 de opción múltiple (4 opciones c/u) + 4 abiertas.

    Usa el resumen y las habilidades ya detectadas en el análisis de CV (candidato.resumen_ia /
    candidato.habilidades_detectadas) en vez de volver a extraer texto del PDF.

    Retorna instancias de PreguntaExamen SIN tenant_id ni examen_id — el llamador (router)
    debe completarlos antes de persistirlas, porque el examen recién se crea después de
    invocar esta función.
    """
    prompt = _construir_prompt_preguntas(candidato, vacante, area)
    resultado = await consultar_gemini_json(prompt)

    preguntas: list[PreguntaExamen] = []
    for orden, item in enumerate(resultado.get("preguntas", []), start=1):
        tipo = _como_tipo_pregunta(item.get("tipo"))
        es_mc = tipo == TipoPregunta.MULTIPLE_CHOICE

        preguntas.append(
            PreguntaExamen(
                tenant_id="",
                examen_id="",
                orden=orden,
                tipo=tipo,
                enunciado=str(item.get("enunciado", "")),
                opciones_json=_como_lista_opciones(item.get("opciones")) if es_mc else None,
                respuesta_correcta=str(item["respuesta_correcta"]) if es_mc and item.get("respuesta_correcta") else None,
                puntos_max=2.0,
            )
        )

    return preguntas


def _construir_prompt_calificacion(preguntas: list[PreguntaExamen]) -> str:
    """Arma el prompt de calificación de las preguntas abiertas de un examen."""
    preguntas_texto = "\n\n".join(
        f"{i}. Pregunta: {p.enunciado}\nRespuesta del candidato: {p.respuesta_candidato or '(sin responder)'}"
        for i, p in enumerate(preguntas, start=1)
    )

    return f"""
Eres un examinador técnico calificando las respuestas abiertas de un examen.

Para cada pregunta, califica la respuesta del candidato con 0, 1 o 2 puntos:
- 0: respuesta incorrecta, vacía o irrelevante
- 1: respuesta parcialmente correcta o incompleta
- 2: respuesta correcta y completa

## Preguntas y respuestas
{preguntas_texto}

## Tarea
Responde ÚNICAMENTE con un JSON (sin texto adicional, sin markdown), en el mismo orden en
que se listaron las preguntas:

{{
  "calificaciones": [
    {{"puntos": <0, 1 o 2>, "feedback": "<retroalimentación breve para el candidato>"}}
  ]
}}
""".strip()


def _como_puntos_abierta(valor: Any) -> float:
    """Normaliza los puntos de una pregunta abierta a 0.0, 1.0 o 2.0."""
    try:
        puntos = round(float(valor))
    except (TypeError, ValueError):
        return 0.0
    return float(max(0, min(2, puntos)))


async def _calificar_abiertas(preguntas: list[PreguntaExamen]) -> dict[str, tuple[float, str]]:
    """Evalúa con Gemini las preguntas abiertas; retorna {pregunta_id: (puntos, feedback)}."""
    if not preguntas:
        return {}

    prompt = _construir_prompt_calificacion(preguntas)
    resultado = await consultar_gemini_json(prompt)
    items = resultado.get("calificaciones", [])

    calificaciones: dict[str, tuple[float, str]] = {}
    for indice, pregunta in enumerate(preguntas):
        item = items[indice] if indice < len(items) else {}
        puntos = _como_puntos_abierta(item.get("puntos"))
        feedback = str(item.get("feedback") or "")
        calificaciones[pregunta.id] = (puntos, feedback)

    return calificaciones


async def calificar_examen(examen_id: str, db: AsyncSession) -> Examen:
    """Califica un examen: MC automático + abiertas evaluadas por Gemini (sección 10 del CLAUDE.md).

    - MC: compara respuesta_candidato con respuesta_correcta → 0 o puntos_max (2.0)
    - Abiertas: Gemini evalúa la respuesta → 0, 1 o 2 puntos, con feedback
    - Nota final = suma de puntos_obtenidos (máximo 20, sobre 6 MC + 4 abiertas × 2 pts)
    - Si nota >= nota_minima_examen de la vacante: candidato pasa a examen_aprobado,
      se emite el token de entrevista y se envía el correo de invitación
    - Si nota < nota_minima_examen: candidato pasa a examen_rechazado, sin correo
    """
    examen = await db.get(Examen, examen_id)
    if examen is None:
        raise ValueError(f"Examen {examen_id} no encontrado")

    statement = select(PreguntaExamen).where(PreguntaExamen.examen_id == examen_id).order_by(PreguntaExamen.orden)
    result = await db.exec(statement)
    preguntas = list(result.all())

    abiertas = [p for p in preguntas if p.tipo == TipoPregunta.ABIERTA]
    calificaciones_abiertas = await _calificar_abiertas(abiertas)

    for pregunta in preguntas:
        if pregunta.tipo == TipoPregunta.MULTIPLE_CHOICE:
            acierto = (
                pregunta.respuesta_candidato is not None
                and pregunta.respuesta_candidato == pregunta.respuesta_correcta
            )
            pregunta.puntos_obtenidos = pregunta.puntos_max if acierto else 0.0
        else:
            puntos, feedback = calificaciones_abiertas.get(pregunta.id, (0.0, ""))
            pregunta.puntos_obtenidos = puntos
            pregunta.feedback_ia = feedback

        db.add(pregunta)

    examen.nota = round(sum(p.puntos_obtenidos or 0.0 for p in preguntas), 2)
    db.add(examen)
    await db.commit()
    await db.refresh(examen)

    candidato = await db.get(Candidato, examen.candidato_id)
    vacante = await db.get(Vacante, examen.vacante_id)
    if candidato is None or vacante is None:
        return examen

    candidato.updated_at = utcnow()

    if examen.nota >= vacante.nota_minima_examen:
        candidato.estado = EstadoCandidato.EXAMEN_APROBADO
        db.add(candidato)
        await db.commit()

        token = await emitir_token_candidato(candidato.id, candidato.tenant_id, TipoToken.ENTREVISTA, db)
        await correo_invitacion_entrevista(candidato, token)
    else:
        candidato.estado = EstadoCandidato.EXAMEN_RECHAZADO
        db.add(candidato)
        await db.commit()

    return examen


async def registrar_evento(examen_id: str, tenant_id: str, tipo: str, detalle: str | None, db: AsyncSession) -> Examen:
    """Registra un evento de proctoring del examen: crea el EventoAuditoria y suma sus puntos
    de riesgo al examen, recalculando el semáforo (catálogo en la sección 11 del CLAUDE.md).
    """
    examen = await db.get(Examen, examen_id)
    if examen is None:
        raise ValueError(f"Examen {examen_id} no encontrado")

    severidad, puntos = CATALOGO_EVENTOS_PROCTORING.get(tipo, EVENTO_DEFAULT)

    evento = EventoAuditoria(
        tenant_id=tenant_id,
        examen_id=examen.id,
        tipo=tipo,
        severidad=severidad,
        detalle=detalle,
    )
    db.add(evento)

    examen.puntaje_riesgo += puntos
    examen.semaforo = calcular_semaforo(examen.puntaje_riesgo)
    db.add(examen)

    await db.commit()
    await db.refresh(examen)

    return examen
