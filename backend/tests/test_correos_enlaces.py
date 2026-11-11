"""El enlace de los correos de avance abre la página de acceso del candidato.

El frontend recibe el token en `/candidato/acceso?token=...` (pages/candidato/Acceso.jsx), que
distingue si es de examen o de entrevista. Una ruta inexistente (`/examen`, `/entrevista`) caía en
la ruta comodín del panel y llevaba al dashboard de RRHH.
"""
import re

import pytest

from app.core.config import settings
from app.models.candidato import Candidato, EstadoCandidato
from app.models.vacante import Vacante
from app.services import correos


@pytest.fixture
def enviados(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    registro: list[str] = []

    async def enviar_falso(destinatario: str, asunto: str, html: str) -> None:
        registro.append(html)

    monkeypatch.setattr(correos, "_enviar_correo", enviar_falso)
    return registro


def _candidato() -> Candidato:
    return Candidato(
        tenant_id="t", vacante_id="v", nombre="Andrés", apellidos="Salazar Huamán",
        email="andres@example.com", estado=EstadoCandidato.CV_APROBADO,
    )


def _enlace(html: str) -> str:
    return re.search(r'href="([^"]+)"', html).group(1)


@pytest.mark.asyncio
async def test_correo_del_examen_lleva_a_la_pagina_de_acceso(enviados: list[str]) -> None:
    await correos.correo_bienvenida_examen(_candidato(), "TOKEN-EXAMEN", Vacante(titulo="Backend"))
    assert _enlace(enviados[0]) == f"{settings.frontend_url}/candidato/acceso?token=TOKEN-EXAMEN"


@pytest.mark.asyncio
async def test_correo_de_la_entrevista_lleva_a_la_pagina_de_acceso(enviados: list[str]) -> None:
    await correos.correo_invitacion_entrevista(_candidato(), "TOKEN-ENTREVISTA", Vacante(titulo="Backend"))
    assert _enlace(enviados[0]) == f"{settings.frontend_url}/candidato/acceso?token=TOKEN-ENTREVISTA"
