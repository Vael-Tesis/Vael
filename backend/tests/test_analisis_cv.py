"""Pruebas de DEC-024 (desglose ponderado y auditable de score_cv) — DEV-C-14, HU-12.

Cubren las cuatro pruebas de la sección "Validación" del ADR: una respuesta válida suma los
cinco criterios en score_cv; un criterio faltante o fuera de rango hace fallar el análisis
por el camino de error existente, sin guardar nada; el detalle del candidato expone
score_desglose; un candidato anterior a esta decisión lo expone como nulo. Ninguna prueba
llama a Gemini real: todas usan respuestas simuladas (`monkeypatch` sobre
`analisis_cv.consultar_gemini_json`), válidas e inválidas.
"""
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import con_tenant
from app.models.area import Area
from app.models.candidato import Candidato, ClasificacionIA, EstadoCandidato
from app.models.usuario import Empresa
from app.models.vacante import EstadoVacante, Vacante
from app.services import analisis_cv
from tests.conftest import TENANT_ID

CRITERIOS_VALIDOS: dict[str, dict[str, Any]] = {
    "match_habilidades": {"puntaje": 35, "justificacion": "Python, FastAPI y PostgreSQL con evidencia de uso"},
    "experiencia": {"puntaje": 17, "justificacion": "Cumple los años pedidos en roles relevantes"},
    "formacion": {"puntaje": 12, "justificacion": "Carrera afín, con institución y fechas"},
    "coherencia": {"puntaje": 11, "justificacion": "El relato se sigue con facilidad"},
    "trayectoria": {"puntaje": 7, "justificacion": "Progresión razonable"},
}
SUMA_CRITERIOS_VALIDOS = 35 + 17 + 12 + 11 + 7  # 82


async def _vacante(db: AsyncSession) -> Vacante:
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    db.add(area)
    await db.flush()
    vacante = Vacante(
        tenant_id=TENANT_ID,
        area_id=area.id,
        codigo="TI-2026-001",
        titulo="Desarrollador Backend Python",
        estado=EstadoVacante.ABIERTA,
        score_cv_minimo=60,
    )
    db.add(vacante)
    db.add(Empresa(tenant_id=TENANT_ID, nombre="Andina Servicios S.A.C.", email_contacto="datos@andina.example.com"))
    await db.commit()
    return vacante


async def _candidato(db: AsyncSession, vacante: Vacante, sufijo: str = "1", **campos: Any) -> Candidato:
    campos.setdefault("estado", EstadoCandidato.CV_ANALIZANDO)
    campos.setdefault("cv_url", "https://s3.example.com/cv.pdf")
    candidato = Candidato(
        tenant_id=TENANT_ID,
        vacante_id=vacante.id,
        nombre="Lucía",
        apellidos=f"Quispe {sufijo}",
        email=f"lucia{sufijo}@example.com",
        **campos,
    )
    db.add(candidato)
    await db.commit()
    return candidato


def _preparar_analisis(monkeypatch: pytest.MonkeyPatch, resultado_gemini: dict[str, Any]) -> None:
    """Simula la descarga del PDF, la extracción de texto y la llamada a Gemini."""

    async def pdf_falso(_url: str) -> bytes:
        return b"%PDF"

    async def gemini_falso(_prompt: str, model_name: str | None = None) -> dict[str, Any]:
        return resultado_gemini

    monkeypatch.setattr(analisis_cv, "descargar_archivo", pdf_falso)
    monkeypatch.setattr(analisis_cv, "extraer_texto_pdf", lambda _b: "Python FastAPI PostgreSQL")
    monkeypatch.setattr(analisis_cv, "consultar_gemini_json", gemini_falso)


# --- 1. Una respuesta válida produce score_cv igual a la suma de los cinco criterios -------


async def test_una_respuesta_valida_suma_los_cinco_criterios(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante)
    _preparar_analisis(
        monkeypatch,
        {
            "criterios": CRITERIOS_VALIDOS,
            "clasificacion": "recomendado",
            "resumen": "Encaja bien con la vacante",
        },
    )

    await analisis_cv.analizar_cv(candidato, vacante, None, db_session)

    assert candidato.score_cv == SUMA_CRITERIOS_VALIDOS
    assert candidato.score_desglose == CRITERIOS_VALIDOS
    assert candidato.clasificacion_ia is ClasificacionIA.RECOMENDADO
    assert candidato.estado is EstadoCandidato.CV_POR_CONFIRMAR


# --- 2. Un criterio faltante o fuera de rango falla por el camino de error existente -------


@pytest.mark.parametrize(
    "criterios_invalidos",
    [
        pytest.param(
            {k: v for k, v in CRITERIOS_VALIDOS.items() if k != "trayectoria"},
            id="falta_un_criterio",
        ),
        pytest.param(
            {**CRITERIOS_VALIDOS, "match_habilidades": {"puntaje": 41, "justificacion": "fuera de rango"}},
            id="fuera_de_rango_por_arriba",
        ),
        pytest.param(
            {**CRITERIOS_VALIDOS, "experiencia": {"puntaje": -1, "justificacion": "fuera de rango"}},
            id="fuera_de_rango_por_abajo",
        ),
        pytest.param(
            {**CRITERIOS_VALIDOS, "formacion": {"puntaje": 12.5, "justificacion": "no es entero"}},
            id="no_es_entero",
        ),
        pytest.param({}, id="sin_ningun_criterio"),
        pytest.param("no es un objeto", id="criterios_no_es_un_dict"),
    ],
)
async def test_un_desglose_invalido_falla_sin_guardar_nada(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, criterios_invalidos: Any
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante)
    _preparar_analisis(
        monkeypatch,
        {"criterios": criterios_invalidos, "clasificacion": "recomendado", "resumen": "Resumen"},
    )

    with pytest.raises(ValueError):
        await analisis_cv.analizar_cv(candidato, vacante, None, db_session)

    # No se ajusta ningún valor en silencio (DEC-024, punto 3): el candidato queda como antes.
    assert candidato.score_cv is None
    assert candidato.score_desglose is None
    assert candidato.estado is EstadoCandidato.CV_ANALIZANDO


async def test_un_desglose_invalido_deja_al_candidato_en_postulado(
    db_session: AsyncSession, db_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A través del punto de entrada de la tarea asíncrona: el camino de error ya existente
    (analizar_cv_candidato) atrapa el ValueError y regresa al candidato a `postulado`."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante)
    criterios_invalidos = {k: v for k, v in CRITERIOS_VALIDOS.items() if k != "coherencia"}
    _preparar_analisis(
        monkeypatch,
        {"criterios": criterios_invalidos, "clasificacion": "recomendado", "resumen": "Resumen"},
    )
    # analizar_cv_candidato abre su propia sesión con async_session_factory: se apunta a la
    # misma base de prueba que db_session, en vez de la base real del entorno.
    monkeypatch.setattr(
        analisis_cv, "async_session_factory", async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    )

    # El tenant de la fila lo fija despachar_tarea con con_tenant(...) antes de invocar al
    # manejador (DEC-016); se reproduce aquí para que la RLS deje ver al candidato.
    with con_tenant(TENANT_ID):
        await analisis_cv.analizar_cv_candidato(candidato.id)

    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.POSTULADO
    assert candidato.score_cv is None
    assert candidato.score_desglose is None


# --- 3. El detalle del candidato expone score_desglose; nulo para un análisis anterior -----


async def test_el_detalle_expone_el_desglose_del_candidato(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(
        db_session, vacante, sufijo="con-desglose",
        estado=EstadoCandidato.CV_POR_CONFIRMAR, score_cv=SUMA_CRITERIOS_VALIDOS, score_desglose=CRITERIOS_VALIDOS,
    )

    respuesta = client.get(f"/api/candidatos/{candidato.id}", headers=admin_headers)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["score_desglose"] == CRITERIOS_VALIDOS


async def test_un_candidato_anterior_a_dec_024_expone_el_desglose_como_nulo(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """Candidato analizado antes de esta decisión: score_cv con el puntaje único anterior,
    score_desglose nulo (DEC-024, punto 5; la pantalla lo indica como "análisis anterior")."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(
        db_session, vacante, sufijo="anterior",
        estado=EstadoCandidato.CV_POR_CONFIRMAR, score_cv=72, score_desglose=None,
    )

    respuesta = client.get(f"/api/candidatos/{candidato.id}", headers=admin_headers)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["score_cv"] == 72
    assert cuerpo["score_desglose"] is None
