"""Servicio de generación de textos de marketing para vacantes con Google Gemini."""
from app.core.gemini import consultar_gemini_json
from app.models.vacante import Vacante


def _construir_prompt_textos_marketing(vacante: Vacante) -> str:
    """Arma el prompt para generar textos de difusión de una vacante en distintos canales."""
    requisitos = vacante.requisitos or "No se especificaron requisitos obligatorios."
    habilidades = ", ".join(vacante.habilidades) if vacante.habilidades else "No especificadas."
    modalidad = vacante.modalidad.value if vacante.modalidad else "no especificada"
    ciudad = vacante.ciudad or "no especificada"

    return f"""
Eres un especialista en marketing de reclutamiento. Escribe textos de difusión para la
siguiente vacante, adaptados a distintos canales.

## Vacante: {vacante.titulo}
Modalidad: {modalidad}
Ciudad: {ciudad}
Requisitos: {requisitos}
Habilidades buscadas: {habilidades}

## Tarea
Escribe un texto de difusión para cada uno de estos canales, con el tono y la longitud
apropiados para cada uno:
- "linkedin": profesional, 3-5 párrafos cortos, puede usar viñetas y hashtags al final.
- "whatsapp": informal y directo, 3-4 líneas, apto para reenviar en un grupo.
- "indeed": descriptivo y neutro, similar a una descripción de puesto estándar, 2-3 párrafos.

Responde ÚNICAMENTE con un JSON (sin texto adicional, sin markdown) con esta forma:

{{
  "linkedin": "<texto>",
  "whatsapp": "<texto>",
  "indeed": "<texto>"
}}
""".strip()


async def generar_textos_marketing(vacante: Vacante) -> dict[str, str]:
    """Genera con Gemini textos de difusión de una vacante para LinkedIn, WhatsApp e Indeed."""
    prompt = _construir_prompt_textos_marketing(vacante)
    resultado = await consultar_gemini_json(prompt)

    return {canal: str(texto) for canal, texto in resultado.items() if isinstance(texto, str)}
