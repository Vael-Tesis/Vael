"""Servicio de decisiones: único autorizado a ejecutar avances y descartes (DEC-009, DEC-013).

La IA deja al candidato en `cv_por_confirmar`, `examen_por_confirmar` o
`entrevista_realizada` con una recomendación. Este servicio registra la decisión humana en
`decisiones_candidato` (solo inserción) y después ejecuta su efecto: estado, token y correo
de la etapa siguiente al avanzar; estado y un único correo de cierre al descartar.

No depende de FastAPI: lanza ErrorDecision y el router la traduce a HTTP.
"""
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import emitir_token_candidato
from app.models.base import utcnow
from app.models.candidato import Candidato, EstadoCandidato
from app.models.decision import DecisionCandidato, EtapaDecision, TipoDecision
from app.models.evaluacion import Examen
from app.models.usuario import Empresa, TipoToken, TokenAcceso, Usuario
from app.models.vacante import Vacante
from app.services.correos import (
    correo_bienvenida_examen,
    correo_cierre_proceso,
    correo_finalista,
    correo_invitacion_entrevista,
)

logger = logging.getLogger(__name__)

# Estado en el que la IA deja al candidato a la espera de la decisión de cada etapa
ESTADO_POR_CONFIRMAR: dict[EtapaDecision, EstadoCandidato] = {
    EtapaDecision.CV: EstadoCandidato.CV_POR_CONFIRMAR,
    EtapaDecision.EXAMEN: EstadoCandidato.EXAMEN_POR_CONFIRMAR,
    EtapaDecision.ENTREVISTA: EstadoCandidato.ENTREVISTA_REALIZADA,
}

# Estado que deja cada decisión (doc 08, tabla del servicio de decisiones)
ESTADO_RESULTANTE: dict[tuple[EtapaDecision, TipoDecision], EstadoCandidato] = {
    (EtapaDecision.CV, TipoDecision.AVANZAR): EstadoCandidato.CV_APROBADO,
    (EtapaDecision.CV, TipoDecision.DESCARTAR): EstadoCandidato.CV_RECHAZADO,
    (EtapaDecision.EXAMEN, TipoDecision.AVANZAR): EstadoCandidato.EXAMEN_APROBADO,
    (EtapaDecision.EXAMEN, TipoDecision.DESCARTAR): EstadoCandidato.EXAMEN_RECHAZADO,
    (EtapaDecision.ENTREVISTA, TipoDecision.AVANZAR): EstadoCandidato.FINALISTA,
    (EtapaDecision.ENTREVISTA, TipoDecision.DESCARTAR): EstadoCandidato.DESCARTADO,
}

# Estados que solo se alcanzan con una decisión humana; cambiar-estado los rechaza
ESTADOS_DE_DECISION_HUMANA = frozenset(ESTADO_RESULTANTE.values())

# Token que emite el avance de cada etapa (la entrevista no emite: termina en finalista)
_TOKEN_DEL_AVANCE: dict[EtapaDecision, TipoToken] = {
    EtapaDecision.CV: TipoToken.EXAMEN,
    EtapaDecision.EXAMEN: TipoToken.ENTREVISTA,
}


class ErrorDecision(Exception):
    """Decisión rechazada. `codigo` es el estado HTTP que debe responder el router."""

    def __init__(self, codigo: int, detalle: str) -> None:
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


@dataclass(frozen=True)
class Recomendacion:
    """Recomendación de la IA para una etapa: sentido, puntaje y criterio aplicado."""

    etapa: EtapaDecision
    recomendacion: TipoDecision | None
    puntaje: float | None
    umbral: float | None
    justificacion: str | None


@dataclass(frozen=True)
class DecisionSolicitada:
    """Datos de una decisión tal como los envía RRHH."""

    etapa: EtapaDecision
    decision: TipoDecision
    justificacion_humana: str | None = None
    revision_inicio: datetime | None = None


def _sentido(puntaje: float | None, umbral: float | None) -> TipoDecision | None:
    if puntaje is None or umbral is None:
        return None
    return TipoDecision.AVANZAR if puntaje >= umbral else TipoDecision.DESCARTAR


async def nota_examen(candidato: Candidato, db: AsyncSession) -> float | None:
    """Nota del examen del candidato en su vacante, o None si aún no la tiene."""
    statement = select(Examen).where(
        Examen.tenant_id == candidato.tenant_id,
        Examen.candidato_id == candidato.id,
        Examen.vacante_id == candidato.vacante_id,
    )
    examen = (await db.exec(statement)).first()
    return examen.nota if examen is not None else None


def recomendacion_de_etapa(
    candidato: Candidato, vacante: Vacante, etapa: EtapaDecision, nota: float | None = None
) -> Recomendacion:
    """Recomendación de la IA para la etapa, con el criterio de la vacante.

    CV: `score_cv` frente a `score_cv_minimo`. Examen: la nota frente a `nota_minima_examen`.
    Entrevista: no hay umbral, así que la recomendación es nula (DEC-009) y el puntaje es el
    `score_final` (DEC-007).
    """
    if etapa is EtapaDecision.CV:
        puntaje = float(candidato.score_cv) if candidato.score_cv is not None else None
        umbral = float(vacante.score_cv_minimo)
        return Recomendacion(etapa, _sentido(puntaje, umbral), puntaje, umbral, candidato.resumen_ia)
    if etapa is EtapaDecision.EXAMEN:
        umbral = float(vacante.nota_minima_examen)
        return Recomendacion(etapa, _sentido(nota, umbral), nota, umbral, None)
    return Recomendacion(etapa, None, candidato.score_final, None, None)


async def calcular_recomendacion(candidato: Candidato, vacante: Vacante, etapa: EtapaDecision, db: AsyncSession) -> Recomendacion:
    """Como recomendacion_de_etapa, pero busca la nota del examen cuando la etapa la necesita."""
    nota = await nota_examen(candidato, db) if etapa is EtapaDecision.EXAMEN else None
    return recomendacion_de_etapa(candidato, vacante, etapa, nota)


async def historial(candidato_id: str, tenant_id: str, db: AsyncSession) -> list[DecisionCandidato]:
    """Decisiones del candidato en orden cronológico."""
    statement = (
        select(DecisionCandidato)
        .where(DecisionCandidato.tenant_id == tenant_id, DecisionCandidato.candidato_id == candidato_id)
        .order_by(DecisionCandidato.decidido_en, DecisionCandidato.id)
    )
    return list((await db.exec(statement)).all())


async def _ultima_decision(candidato_id: str, tenant_id: str, etapa: EtapaDecision, db: AsyncSession) -> DecisionCandidato | None:
    decisiones = [d for d in await historial(candidato_id, tenant_id, db) if d.etapa == etapa]
    return decisiones[-1] if decisiones else None


async def _hubo_descarte(candidato_id: str, tenant_id: str, db: AsyncSession) -> bool:
    """Si ya se confirmó algún descarte del candidato, el correo de cierre ya salió (DEC-013, punto 4)."""
    statement = select(DecisionCandidato.id).where(
        DecisionCandidato.tenant_id == tenant_id,
        DecisionCandidato.candidato_id == candidato_id,
        DecisionCandidato.decision == TipoDecision.DESCARTAR,
    )
    return (await db.exec(statement)).first() is not None


async def _invalidar_tokens(candidato: Candidato, tipo: TipoToken, db: AsyncSession) -> None:
    """Al revertir un avance a descarte, el token que ese avance emitió deja de servir."""
    statement = select(TokenAcceso).where(
        TokenAcceso.tenant_id == candidato.tenant_id,
        TokenAcceso.candidato_id == candidato.id,
        TokenAcceso.tipo == tipo,
        TokenAcceso.usado.is_(False),
    )
    for token in (await db.exec(statement)).all():
        token.usado = True
        db.add(token)


async def _obtener_candidato(candidato_id: str, tenant_id: str, db: AsyncSession) -> tuple[Candidato, Vacante]:
    statement = select(Candidato).where(Candidato.id == candidato_id, Candidato.tenant_id == tenant_id)
    candidato = (await db.exec(statement)).first()
    if candidato is None:
        raise ErrorDecision(404, "Candidato no encontrado")
    vacante = await db.get(Vacante, candidato.vacante_id)
    if vacante is None or vacante.tenant_id != tenant_id:
        raise ErrorDecision(404, "Vacante no encontrada")
    return candidato, vacante


@dataclass
class _Preparada:
    candidato: Candidato
    vacante: Vacante
    recomendacion: Recomendacion
    coincide: bool | None
    reemplaza_a: DecisionCandidato | None
    existente: DecisionCandidato | None


async def _preparar(
    candidato_id: str, tenant_id: str, solicitud: DecisionSolicitada, db: AsyncSession, *, solo_si_coincide: bool
) -> _Preparada:
    """Valida la decisión sin escribir nada."""
    candidato, vacante = await _obtener_candidato(candidato_id, tenant_id, db)
    etapa = solicitud.etapa
    ultima = await _ultima_decision(candidato.id, tenant_id, etapa, db)

    if candidato.estado == ESTADO_POR_CONFIRMAR[etapa]:
        # Pendiente de decisión. Si ya hubo una (p. ej. el CV se reanalizó), la nueva la reemplaza.
        reemplaza_a, existente = ultima, None
    elif ultima is not None and candidato.estado == ESTADO_RESULTANTE[(etapa, ultima.decision)]:
        # Ya decidida y sin avanzar a la etapa siguiente: repetirla es idempotente; cambiarla, revertir.
        if solicitud.decision == ultima.decision:
            reemplaza_a, existente = None, ultima
        else:
            reemplaza_a, existente = ultima, None
    else:
        raise ErrorDecision(409, f"El candidato no tiene una decisión pendiente en la etapa {etapa.value}")

    recomendacion = await calcular_recomendacion(candidato, vacante, etapa, db)
    coincide = None if recomendacion.recomendacion is None else solicitud.decision == recomendacion.recomendacion

    if solo_si_coincide and coincide is not True:
        raise ErrorDecision(
            422,
            f"El candidato {candidato.id} no puede decidirse en lote: la decisión no coincide con la "
            "recomendación de la IA o no hay recomendación. Decídelo de forma individual",
        )
    if existente is None and coincide is False and not (solicitud.justificacion_humana or "").strip():
        raise ErrorDecision(422, "Una decisión contraria a la recomendación de la IA exige justificacion_humana")

    return _Preparada(candidato, vacante, recomendacion, coincide, reemplaza_a, existente)


async def _ejecutar(
    preparada: _Preparada, solicitud: DecisionSolicitada, actor: Usuario, db: AsyncSession
) -> DecisionCandidato:
    """Inserta la decisión, cambia el estado y después emite el token y envía el correo."""
    candidato, etapa, decision = preparada.candidato, solicitud.etapa, solicitud.decision
    enviar_cierre = decision is TipoDecision.DESCARTAR and not await _hubo_descarte(candidato.id, candidato.tenant_id, db)

    fila = DecisionCandidato(
        tenant_id=candidato.tenant_id,
        candidato_id=candidato.id,
        etapa=etapa,
        recomendacion_ia=preparada.recomendacion.recomendacion,
        puntaje=preparada.recomendacion.puntaje,
        umbral=preparada.recomendacion.umbral,
        justificacion_ia=preparada.recomendacion.justificacion,
        decision=decision,
        coincide_con_ia=preparada.coincide,
        justificacion_humana=(solicitud.justificacion_humana or "").strip() or None,
        decidido_por=actor.id,
        revision_inicio=solicitud.revision_inicio,
        reemplaza_a=preparada.reemplaza_a.id if preparada.reemplaza_a else None,
    )
    db.add(fila)

    candidato.estado = ESTADO_RESULTANTE[(etapa, decision)]
    candidato.es_finalista = candidato.estado == EstadoCandidato.FINALISTA
    candidato.updated_at = utcnow()
    db.add(candidato)
    if decision is TipoDecision.DESCARTAR and etapa in _TOKEN_DEL_AVANCE:
        await _invalidar_tokens(candidato, _TOKEN_DEL_AVANCE[etapa], db)
    await db.commit()
    await db.refresh(fila)
    await db.refresh(candidato)

    # La decisión ya quedó registrada; si el correo falla se registra y RRHH puede reenviarlo
    # con reenviar-correo-etapa.
    try:
        await _notificar(candidato, preparada.vacante, etapa, decision, enviar_cierre, db)
    except Exception:
        logger.exception("Decisión %s registrada, pero falló su notificación", fila.id, extra={"candidato_id": candidato.id})
    return fila


async def _notificar(
    candidato: Candidato,
    vacante: Vacante,
    etapa: EtapaDecision,
    decision: TipoDecision,
    enviar_cierre: bool,
    db: AsyncSession,
) -> None:
    if decision is TipoDecision.DESCARTAR:
        if enviar_cierre:
            empresa = (await db.exec(select(Empresa).where(Empresa.tenant_id == candidato.tenant_id))).first()
            await correo_cierre_proceso(candidato, vacante, empresa)
        return
    if etapa is EtapaDecision.ENTREVISTA:
        await correo_finalista(candidato, vacante)
        return
    token = await emitir_token_candidato(candidato.id, candidato.tenant_id, _TOKEN_DEL_AVANCE[etapa], db)
    if etapa is EtapaDecision.CV:
        await correo_bienvenida_examen(candidato, token, vacante)
    else:
        await correo_invitacion_entrevista(candidato, token, vacante)


async def registrar_decision(
    candidato_id: str, solicitud: DecisionSolicitada, actor: Usuario, db: AsyncSession
) -> DecisionCandidato:
    """Registra una decisión individual y ejecuta su efecto.

    Si el candidato ya tiene esa misma decisión vigente en la etapa, la devuelve sin insertar
    otra fila ni reenviar correos (idempotencia). Una decisión distinta de la vigente la
    revierte: se inserta una fila nueva con `reemplaza_a`.
    """
    preparada = await _preparar(candidato_id, actor.tenant_id, solicitud, db, solo_si_coincide=False)
    if preparada.existente is not None:
        return preparada.existente
    return await _ejecutar(preparada, solicitud, actor, db)


async def registrar_decisiones_lote(
    etapa: EtapaDecision,
    decisiones: list[tuple[str, TipoDecision]],
    revision_inicio: datetime | None,
    actor: Usuario,
    db: AsyncSession,
) -> list[DecisionCandidato]:
    """Confirma varias recomendaciones a la vez (DEC-009, punto 4).

    Solo acepta decisiones que coinciden con la recomendación de la IA. Valida todo el lote
    antes de escribir: si una decisión no cumple, no se ejecuta ninguna.
    """
    if len({candidato_id for candidato_id, _ in decisiones}) != len(decisiones):
        raise ErrorDecision(422, "El lote repite un candidato")

    solicitudes = [(cid, DecisionSolicitada(etapa, dec, None, revision_inicio)) for cid, dec in decisiones]
    preparadas = [
        (await _preparar(cid, actor.tenant_id, solicitud, db, solo_si_coincide=True), solicitud)
        for cid, solicitud in solicitudes
    ]

    resultado: list[DecisionCandidato] = []
    for preparada, solicitud in preparadas:
        if preparada.existente is not None:
            resultado.append(preparada.existente)
        else:
            resultado.append(await _ejecutar(preparada, solicitud, actor, db))
    return resultado


async def recomendaciones_pendientes(
    tenant_id: str, db: AsyncSession, *, vacante_id: str | None = None, etapa: EtapaDecision | None = None
) -> list[tuple[Candidato, Recomendacion]]:
    """Bandeja: candidatos a la espera de una decisión, con la recomendación de la IA.

    Sin etapa, muestra las de CV y examen (doc 15); la de entrevista se decide desde el ranking.
    """
    etapas = [etapa] if etapa is not None else [EtapaDecision.CV, EtapaDecision.EXAMEN]
    estados = {ESTADO_POR_CONFIRMAR[e]: e for e in etapas}

    statement = select(Candidato).where(Candidato.tenant_id == tenant_id, Candidato.estado.in_(list(estados)))
    if vacante_id is not None:
        statement = statement.where(Candidato.vacante_id == vacante_id)
    candidatos = list((await db.exec(statement.order_by(Candidato.updated_at))).all())
    if not candidatos:
        return []

    vacantes_ids = {c.vacante_id for c in candidatos}
    vacantes = {
        v.id: v
        for v in (await db.exec(select(Vacante).where(Vacante.tenant_id == tenant_id, Vacante.id.in_(vacantes_ids)))).all()
    }
    notas = {
        e.candidato_id: e.nota
        for e in (
            await db.exec(
                select(Examen).where(Examen.tenant_id == tenant_id, Examen.candidato_id.in_([c.id for c in candidatos]))
            )
        ).all()
    }
    return [
        (c, recomendacion_de_etapa(c, vacantes[c.vacante_id], estados[c.estado], notas.get(c.id)))
        for c in candidatos
        if c.vacante_id in vacantes
    ]
