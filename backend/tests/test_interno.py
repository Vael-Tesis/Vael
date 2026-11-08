"""Endpoint interno de las Lambdas con firma HMAC (DEV-C-13 · HU-23, DEC-018).

Cubre la validación de DEC-018 ("el endpoint interno rechaza peticiones sin firma, con firma
inválida o con una marca de tiempo vencida") y las de DEC-016 (idempotencia y tenant del
mensaje): una entrega repetida no cambia nada y un mensaje con otro tenant no toca filas ajenas.
"""
import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.interno import CABECERA_FIRMA, CABECERA_MARCA, VENTANA_SEGUNDOS, firmar, verificar_firma
from app.main import app
from app.models.area import Area
from app.models.candidato import Candidato, ClasificacionIA, EstadoCandidato
from app.models.decision import DecisionCandidato
from app.models.entrevista import EntrevistaIA, EstadoEntrevista
from app.models.evaluacion import Examen
from app.models.vacante import EstadoVacante, Vacante
from app.services.analisis_cv import MENSAJE_CV_SIN_TEXTO
from tests.conftest import TENANT_ID, TENANT_ID_OTRO

RUTA_CV = "/api/interno/resultados/analisis-cv"
RUTA_ENTREVISTA = "/api/interno/resultados/analisis-entrevista"

DESGLOSE = {
    "match_habilidades": {"puntaje": 35, "justificacion": "Python y FastAPI con evidencia"},
    "experiencia": {"puntaje": 18, "justificacion": "Cumple los años"},
    "formacion": {"puntaje": 12, "justificacion": "Carrera afín"},
    "coherencia": {"puntaje": 12, "justificacion": "Relato claro"},
    "trayectoria": {"puntaje": 8, "justificacion": "Progresión estable"},
}


def _enviar(client: TestClient, ruta: str, cuerpo: dict[str, Any], marca: int | None = None) -> Any:
    datos = json.dumps(cuerpo).encode()
    marca_texto, firma = firmar(datos, marca)
    return client.post(ruta, content=datos, headers={"Content-Type": "application/json", CABECERA_MARCA: marca_texto, CABECERA_FIRMA: firma})


async def _candidato(db: AsyncSession, estado: EstadoCandidato = EstadoCandidato.CV_ANALIZANDO, **campos: Any) -> Candidato:
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    db.add(area)
    await db.flush()
    vacante = Vacante(tenant_id=TENANT_ID, area_id=area.id, codigo="TI-2026-950", titulo="Backend", estado=EstadoVacante.ABIERTA)
    db.add(vacante)
    await db.flush()
    candidato = Candidato(
        tenant_id=TENANT_ID, vacante_id=vacante.id, nombre="Rosa", apellidos="Mendoza",
        email="rosa.interno@example.com", estado=estado, **campos,
    )
    db.add(candidato)
    await db.commit()
    return candidato


def _resultado_cv(candidato: Candidato, **cambios: Any) -> dict[str, Any]:
    return {
        "tenant_id": candidato.tenant_id,
        "candidato_id": candidato.id,
        "sin_texto": False,
        "score_cv": 85,
        "score_desglose": DESGLOSE,
        "clasificacion": "altamente_recomendado",
        "resumen": "Encaja muy bien con la vacante.",
        "habilidades_detectadas": ["Python", "FastAPI"],
        "inconsistencias": [],
        "linkedin": None,
        "github": "https://github.com/rosa",
        "portfolio": None,
        **cambios,
    }


# --- Firma HMAC (DEC-018) -------------------------------------------------------------


def test_la_firma_es_valida_solo_para_el_mismo_cuerpo() -> None:
    marca, firma = firmar(b'{"a":1}')
    assert verificar_firma(b'{"a":1}', marca, firma)
    assert not verificar_firma(b'{"a":2}', marca, firma)


@pytest.mark.parametrize("desfase", [VENTANA_SEGUNDOS + 60, -(VENTANA_SEGUNDOS + 60)])
def test_una_marca_fuera_de_la_ventana_se_rechaza(desfase: int) -> None:
    marca, firma = firmar(b"{}", int(time.time()) - desfase)
    assert not verificar_firma(b"{}", marca, firma)


@pytest.mark.parametrize(
    "cabeceras",
    [
        {},
        {CABECERA_MARCA: str(int(time.time()))},
        {CABECERA_MARCA: str(int(time.time())), CABECERA_FIRMA: "0" * 64},
        {CABECERA_MARCA: "no-es-un-numero", CABECERA_FIRMA: "0" * 64},
    ],
    ids=["sin-cabeceras", "sin-firma", "firma-invalida", "marca-invalida"],
)
@pytest.mark.parametrize("ruta", [RUTA_CV, RUTA_ENTREVISTA])
def test_sin_firma_valida_responde_401(client: TestClient, ruta: str, cabeceras: dict[str, str]) -> None:
    respuesta = client.post(ruta, content=b"{}", headers={"Content-Type": "application/json", **cabeceras})
    assert respuesta.status_code == 401


async def test_una_entrega_vencida_se_rechaza_y_no_cambia_nada(client: TestClient, db_session: AsyncSession) -> None:
    candidato = await _candidato(db_session)
    vieja = int(time.time()) - VENTANA_SEGUNDOS - 1

    respuesta = _enviar(client, RUTA_CV, _resultado_cv(candidato), marca=vieja)

    assert respuesta.status_code == 401
    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.CV_ANALIZANDO


async def test_un_cuerpo_alterado_despues_de_firmar_se_rechaza(client: TestClient, db_session: AsyncSession) -> None:
    candidato = await _candidato(db_session)
    original = json.dumps(_resultado_cv(candidato)).encode()
    marca, firma = firmar(original)
    alterado = json.dumps(_resultado_cv(candidato, score_cv=99)).encode()

    respuesta = client.post(RUTA_CV, content=alterado, headers={"Content-Type": "application/json", CABECERA_MARCA: marca, CABECERA_FIRMA: firma})

    assert respuesta.status_code == 401


def test_las_rutas_internas_no_estan_en_el_openapi() -> None:
    assert not [ruta for ruta in app.openapi()["paths"] if ruta.startswith("/api/interno")]


# --- Resultado del análisis de CV -----------------------------------------------------


async def test_aplica_el_resultado_y_deja_la_decision_a_rrhh(client: TestClient, db_session: AsyncSession) -> None:
    candidato = await _candidato(db_session)

    respuesta = _enviar(client, RUTA_CV, _resultado_cv(candidato))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"aplicado": True}
    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.CV_POR_CONFIRMAR  # DEC-009: la IA recomienda
    assert candidato.score_cv == 85
    assert candidato.score_desglose == DESGLOSE
    assert candidato.clasificacion_ia is ClasificacionIA.ALTAMENTE_RECOMENDADO
    assert candidato.github == "https://github.com/rosa"
    decisiones = (await db_session.exec(select(DecisionCandidato).where(DecisionCandidato.candidato_id == candidato.id))).all()
    assert decisiones == []


async def test_una_entrega_repetida_no_cambia_nada(client: TestClient, db_session: AsyncSession) -> None:
    """SQS entrega al menos una vez: la segunda entrega responde aplicado=false (DEC-016, punto 7)."""
    candidato = await _candidato(db_session)
    assert _enviar(client, RUTA_CV, _resultado_cv(candidato)).json() == {"aplicado": True}

    segunda = _enviar(client, RUTA_CV, _resultado_cv(candidato, score_cv=40, score_desglose=DESGLOSE))

    assert segunda.status_code == 200
    assert segunda.json() == {"aplicado": False}
    await db_session.refresh(candidato)
    assert candidato.score_cv == 85


async def test_no_pisa_una_decision_ya_tomada(client: TestClient, db_session: AsyncSession) -> None:
    candidato = await _candidato(db_session, estado=EstadoCandidato.CV_APROBADO, score_cv=70)

    respuesta = _enviar(client, RUTA_CV, _resultado_cv(candidato))

    assert respuesta.json() == {"aplicado": False}
    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.CV_APROBADO
    assert candidato.score_cv == 70


async def test_un_mensaje_con_otro_tenant_no_toca_filas_ajenas(client: TestClient, db_session: AsyncSession) -> None:
    """El tenant viene del mensaje firmado; con la RLS, otra empresa no ve al candidato (DEC-010)."""
    candidato = await _candidato(db_session)

    respuesta = _enviar(client, RUTA_CV, _resultado_cv(candidato, tenant_id=TENANT_ID_OTRO))

    assert respuesta.json() == {"aplicado": False}
    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.CV_ANALIZANDO
    assert candidato.score_cv is None


async def test_un_cv_sin_texto_queda_para_revision_manual(client: TestClient, db_session: AsyncSession) -> None:
    candidato = await _candidato(db_session)

    respuesta = _enviar(client, RUTA_CV, {"tenant_id": TENANT_ID, "candidato_id": candidato.id, "sin_texto": True})

    assert respuesta.json() == {"aplicado": True}
    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.CV_POR_CONFIRMAR
    assert candidato.clasificacion_ia is ClasificacionIA.REQUIERE_REVISION
    assert candidato.resumen_ia == MENSAJE_CV_SIN_TEXTO
    assert candidato.score_cv is None


@pytest.mark.parametrize(
    "cambios",
    [{"score_cv": None}, {"score_desglose": None}, {"score_cv": 101}, {"tenant_id": ""}],
    ids=["sin-score", "sin-desglose", "score-fuera-de-rango", "sin-tenant"],
)
async def test_un_resultado_incompleto_responde_422(client: TestClient, db_session: AsyncSession, cambios: dict[str, Any]) -> None:
    candidato = await _candidato(db_session)

    respuesta = _enviar(client, RUTA_CV, _resultado_cv(candidato, **cambios))

    assert respuesta.status_code == 422
    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.CV_ANALIZANDO


# --- Resultado del análisis de la entrevista ------------------------------------------


async def _entrevista_finalizada(db: AsyncSession) -> tuple[Candidato, EntrevistaIA]:
    candidato = await _candidato(db, estado=EstadoCandidato.ENTREVISTA_PENDIENTE, score_cv=80)
    examen = Examen(tenant_id=TENANT_ID, candidato_id=candidato.id, vacante_id=candidato.vacante_id, nota=15.0)
    entrevista = EntrevistaIA(
        tenant_id=TENANT_ID, candidato_id=candidato.id, vacante_id=candidato.vacante_id,
        estado=EstadoEntrevista.FINALIZADA, transcripcion="EVA: ... Candidato: ...",
    )
    db.add_all([examen, entrevista])
    await db.commit()
    return candidato, entrevista


async def test_aplica_la_nota_de_la_entrevista_y_el_score_final(client: TestClient, db_session: AsyncSession) -> None:
    candidato, entrevista = await _entrevista_finalizada(db_session)
    cuerpo = {"tenant_id": TENANT_ID, "entrevista_id": entrevista.id, "nota": 16.0,
              "dimensiones_json": {"Comunicación": {"nota": 8, "puntaje_maximo": 10, "peso": 100, "comentario": "Clara"}}}

    primera = _enviar(client, RUTA_ENTREVISTA, cuerpo)
    segunda = _enviar(client, RUTA_ENTREVISTA, {**cuerpo, "nota": 5.0})

    assert primera.json() == {"aplicado": True}
    assert segunda.json() == {"aplicado": False}
    await db_session.refresh(entrevista)
    await db_session.refresh(candidato)
    assert entrevista.nota == 16.0
    assert candidato.estado is EstadoCandidato.ENTREVISTA_REALIZADA
    # DEC-007: (80/5)*0.20 + 15*0.40 + 16*0.40 = 3.2 + 6.0 + 6.4
    assert candidato.score_final == pytest.approx(15.6)
