"""RF-A-10 (HU-12): el detalle del candidato muestra el análisis completo de la IA — puntaje,
clasificación, resumen, habilidades, inconsistencias y justificación — y nunca datos de
emociones (DEC-001; la guarda estructural está en test_sin_emociones.py)."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.base import utcnow
from app.models.candidato import ClasificacionIA, EstadoCandidato
from tests.test_decisiones import _candidato, _vacante


async def test_el_detalle_del_candidato_muestra_el_analisis_completo_sin_emociones(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=78, sufijo="analisis")
    candidato.match_porcentaje = 82.5
    candidato.clasificacion_ia = ClasificacionIA.RECOMENDADO
    candidato.habilidades_detectadas = ["Python", "FastAPI", "PostgreSQL"]
    candidato.inconsistencias = ["El CV dice 5 años de experiencia; LinkedIn muestra 3"]
    candidato.analizado_en = utcnow()
    db_session.add(candidato)
    await db_session.commit()

    respuesta = client.get(f"/api/candidatos/{candidato.id}", headers=admin_headers)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["score_cv"] == 78
    assert cuerpo["match_porcentaje"] == 82.5
    assert cuerpo["clasificacion_ia"] == "recomendado"
    assert cuerpo["resumen_ia"]
    assert cuerpo["habilidades_detectadas"] == ["Python", "FastAPI", "PostgreSQL"]
    assert cuerpo["inconsistencias"] == ["El CV dice 5 años de experiencia; LinkedIn muestra 3"]
    assert isinstance(datetime.fromisoformat(cuerpo["analizado_en"]), datetime)

    # DEC-001: ningún campo del análisis (ni de ninguna otra parte de la respuesta) habla de emociones.
    texto = respuesta.text.lower()
    for palabra in ("emocion", "emotion", "sentimiento", "sentiment"):
        assert palabra not in texto, f"La respuesta menciona '{palabra}': {respuesta.text}"
