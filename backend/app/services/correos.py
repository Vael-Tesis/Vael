"""Servicio de envío de correos transaccionales (SES / SMTP) con plantillas Jinja2."""
import logging
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.candidato import Candidato, EstadoCandidato
from app.models.usuario import Usuario
from app.models.vacante import Vacante
from app.services.aws_services import enviar_correo as ses_enviar_correo

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=select_autoescape(["html"]))

# Nunca se envía correo a un candidato en alguno de estos estados (rechazo/descarte).
_ESTADOS_RECHAZADOS = frozenset(
    {
        EstadoCandidato.CV_RECHAZADO,
        EstadoCandidato.EXAMEN_RECHAZADO,
        EstadoCandidato.DESCARTADO,
    }
)


def _puede_recibir_correo(candidato: Candidato) -> bool:
    """Un candidato en estado de rechazo/descarte nunca recibe correos (sección 10 del CLAUDE.md)."""
    if candidato.estado in _ESTADOS_RECHAZADOS:
        logger.warning("Correo NO enviado — candidato %s está en estado %s", candidato.id, candidato.estado)
        return False
    return True


def _render(template_name: str, **contexto: Any) -> str:
    """Renderiza una plantilla HTML de Jinja2 con el contexto dado."""
    plantilla = _env.get_template(template_name)
    return plantilla.render(**contexto)


async def _obtener_titulo_vacante(vacante_id: str) -> str:
    """Resuelve el título de una vacante en una sesión propia (los correos no reciben db)."""
    async with async_session_factory() as db:
        vacante = await db.get(Vacante, vacante_id)
        return vacante.titulo if vacante else "la vacante"


async def _enviar_por_smtp(destinatario: str, asunto: str, html: str) -> None:
    """Envía un correo por SMTP local (desarrollo) — p. ej. Mailhog/aiosmtpd en localhost:1025."""
    mensaje = EmailMessage()
    mensaje["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content("Este correo requiere un cliente compatible con HTML.")
    mensaje.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        mensaje,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=settings.smtp_user is not None,
    )


async def _enviar_correo(destinatario: str, asunto: str, html: str) -> None:
    """Despacha el envío: SES en producción (vía aws_services.py), SMTP local en desarrollo."""
    if settings.is_production:
        enviado = await ses_enviar_correo(
            to=destinatario,
            subject=asunto,
            html_body=html,
            from_email=f"{settings.email_from_name} <{settings.email_from}>",
        )
        if not enviado:
            logger.error("No se pudo enviar el correo a %s vía SES — ver log anterior para el detalle", destinatario)
    else:
        await _enviar_por_smtp(destinatario, asunto, html)


async def correo_bienvenida_examen(candidato: Candidato, token: str) -> None:
    """Correo de invitación al examen técnico — solo si el candidato no está rechazado."""
    if not _puede_recibir_correo(candidato):
        return

    vacante_titulo = await _obtener_titulo_vacante(candidato.vacante_id)
    html = _render(
        "correo_bienvenida_examen.html",
        candidato=candidato,
        vacante_titulo=vacante_titulo,
        link_examen=f"{settings.frontend_url}/examen?token={token}",
    )
    await _enviar_correo(candidato.email, f"Tu evaluación técnica está lista — {vacante_titulo}", html)


async def correo_invitacion_entrevista(candidato: Candidato, token: str) -> None:
    """Correo de invitación a la entrevista con EVA — solo si el candidato no está rechazado."""
    if not _puede_recibir_correo(candidato):
        return

    vacante_titulo = await _obtener_titulo_vacante(candidato.vacante_id)
    html = _render(
        "correo_invitacion_entrevista.html",
        candidato=candidato,
        vacante_titulo=vacante_titulo,
        link_entrevista=f"{settings.frontend_url}/entrevista?token={token}",
    )
    await _enviar_correo(
        candidato.email,
        f"¡Felicitaciones! Pasaste al siguiente paso — {vacante_titulo}",
        html,
    )


async def correo_finalista(candidato: Candidato, vacante: Vacante) -> None:
    """Correo de finalista — solo si el candidato no está rechazado."""
    if not _puede_recibir_correo(candidato):
        return

    html = _render("correo_finalista.html", candidato=candidato, vacante_titulo=vacante.titulo)
    await _enviar_correo(candidato.email, f"Eres finalista en {vacante.titulo}", html)


async def correo_credenciales_usuario(usuario: Usuario, password_temporal: str) -> None:
    """Correo de bienvenida con credenciales para un usuario RRHH recién creado.

    No aplica el filtro de "candidato rechazado" — es para usuarios internos de la
    plataforma, no para candidatos del proceso de selección.
    """
    html = _render(
        "correo_credenciales_usuario.html",
        usuario=usuario,
        password_temporal=password_temporal,
        link_sistema=settings.frontend_url,
    )
    await _enviar_correo(usuario.email, "Bienvenido a VAEL — Tus credenciales de acceso", html)
