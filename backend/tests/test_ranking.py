"""Pruebas del ranking de candidatos (RF-A-14, HU-17) y de la recomendación de finalistas
que usa para decidir en lote (DEC-022) — DEV-A-06.
"""
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.candidato import EstadoCandidato
from tests.test_decisiones import _candidato, _finalista, _vacante, enviados  # noqa: F401


async def test_ranking_ordena_por_score_final_y_separa_los_procesos_incompletos(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]  # noqa: F811
) -> None:
    """Los candidatos con score_final van primero, de mayor a menor; los incompletos aparte."""
    vacante = await _vacante(db_session)
    vacante.top_candidatos_finalistas = 1
    db_session.add(vacante)
    await db_session.commit()
    bajo = await _finalista(db_session, vacante, 14, "a")
    alto = await _finalista(db_session, vacante, 18, "b")
    incompleto = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_PENDIENTE, score_cv=70, sufijo="c")

    respuesta = client.get("/api/candidatos/ranking", params={"vacante_id": vacante.id}, headers=admin_headers)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert [c["id"] for c in cuerpo] == [alto.id, bajo.id, incompleto.id]
    assert [c["proceso_completo"] for c in cuerpo] == [True, True, False]
    assert cuerpo[0]["recomendacion_finalista"] == "avanzar"
    assert cuerpo[1]["recomendacion_finalista"] == "descartar"
    assert cuerpo[2]["recomendacion_finalista"] is None


async def test_ranking_de_una_vacante_inexistente_responde_404(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    respuesta = client.get("/api/candidatos/ranking", params={"vacante_id": "no-existe"}, headers=admin_headers)
    assert respuesta.status_code == 404
