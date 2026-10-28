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
from app.models.usuario import Empresa, Usuario
from app.models.vacante import Vacante
from app.services.aws_services import enviar_correo as ses_enviar_correo

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=select_autoescape(["html"]))

# Estados de descarte confirmado por RRHH (DEC-009). A un candidato en ellos solo se le
# envía el correo de cierre; los correos de avance quedan bloqueados (DEC-013, punto 5).
ESTADOS_DESCARTE = frozenset(
    {
        EstadoCandidato.CV_RECHAZADO,
        EstadoCandidato.EXAMEN_RECHAZADO,
        EstadoCandidato.DESCARTADO,
    }
)


def _puede_recibir_correo_de_avance(candidato: Candidato) -> bool:
    """Un candidato descartado nunca recibe un correo de avance (DEC-013)."""
    if candidato.estado in ESTADOS_DESCARTE:
        logger.warning("Correo de avance NO enviado — candidato %s está en estado %s", candidato.id, candidato.estado)
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
        # `SMTP_USER=` vacío (Mailpit, DEC-023) equivale a sin autenticación ni STARTTLS
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=bool(settings.smtp_user),
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


async def correo_bienvenida_examen(candidato: Candidato, token: str, vacante: Vacante | None = None) -> None:
    """Correo de invitación al examen técnico — nunca a un candidato descartado."""
    if not _puede_recibir_correo_de_avance(candidato):
        return

    vacante_titulo = vacante.titulo if vacante else await _obtener_titulo_vacante(candidato.vacante_id)
    html = _render(
        "correo_bienvenida_examen.html",
        candidato=candidato,
        vacante_titulo=vacante_titulo,
        link_examen=f"{settings.frontend_url}/examen?token={token}",
    )
    await _enviar_correo(candidato.email, f"Tu evaluación técnica está lista — {vacante_titulo}", html)


async def correo_invitacion_entrevista(candidato: Candidato, token: str, vacante: Vacante | None = None) -> None:
    """Correo de invitación a la entrevista con EVA — nunca a un candidato descartado."""
    if not _puede_recibir_correo_de_avance(candidato):
        return

    vacante_titulo = vacante.titulo if vacante else await _obtener_titulo_vacante(candidato.vacante_id)
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
    """Correo de finalista — nunca a un candidato descartado."""
    if not _puede_recibir_correo_de_avance(candidato):
        return

    html = _render("correo_finalista.html", candidato=candidato, vacante_titulo=vacante.titulo)
    await _enviar_correo(candidato.email, f"Eres finalista en {vacante.titulo}", html)


async def correo_cierre_proceso(candidato: Candidato, vacante: Vacante, empresa: Empresa | None) -> bool:
    """Correo único de cierre al candidato cuyo descarte confirmó RRHH (DEC-013).

    Agradece la postulación, avisa que el proceso no continúa, informa que la evaluación usó
    IA con revisión humana y da un contacto para consultas sobre datos personales. No incluye
    puntajes, notas, razones ni justificaciones de la IA. Retorna False si no se envió.
    """
    if candidato.estado not in ESTADOS_DESCARTE:
        logger.warning("Correo de cierre NO enviado — candidato %s no está descartado (%s)", candidato.id, candidato.estado)
        return False

    html = _render(
        "correo_cierre_proceso.html",
        candidato_nombre=candidato.nombre,
        vacante_titulo=vacante.titulo,
        empresa_nombre=empresa.nombre if empresa else None,
        email_contacto=empresa.email_contacto if empresa else None,
    )
    await _enviar_correo(candidato.email, f"Actualización de tu postulación — {vacante.titulo}", html)
    return True


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
