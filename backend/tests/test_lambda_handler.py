"""Lambda de análisis (DEV-C-13 · HU-23, DEC-016, DEC-018).

La Lambda calcula sin tocar la base y entrega el resultado firmado. Se prueba de punta a punta
contra la aplicación real (ASGI): un mensaje de SQS de análisis de CV termina con el candidato
en `cv_por_confirmar`. Un mensaje fallido se informa a SQS para que lo reintente y, agotados
los reintentos, lo mande a la DLQ.
"""
import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app import lambda_handler
from app.core.config import settings
from app.core.interno import CABECERA_FIRMA, CABECERA_MARCA, verificar_firma
from app.main import app
from app.models.area import Area
from app.models.candidato import Candidato, EstadoCandidato
from app.models.vacante import EstadoVacante, Vacante
from app.services import analisis_cv
from tests.conftest import TENANT_ID

CRITERIOS = {
    "match_habilidades": {"puntaje": 30, "justificacion": "a"},
    "experiencia": {"puntaje": 15, "justificacion": "b"},
    "formacion": {"puntaje": 10, "justificacion": "c"},
    "coherencia": {"puntaje": 10, "justificacion": "d"},
    "trayectoria": {"puntaje": 5, "justificacion": "e"},
}


def _registro(mensaje: dict[str, Any], mensaje_id: str = "m-1") -> dict[str, Any]:
    return {"messageId": mensaje_id, "body": json.dumps(mensaje)}


def test_un_mensaje_correcto_no_se_informa_como_fallido(monkeypatch: pytest.MonkeyPatch) -> None:
    entregas: list[tuple[str, dict[str, Any]]] = []

    async def calcular(mensaje: dict[str, Any]) -> dict[str, Any]:
        return {"tenant_id": mensaje["tenant_id"], "candidato_id": mensaje["candidato_id"], "sin_texto": True}

    async def entregar(ruta: str, resultado: dict[str, Any]) -> None:
        entregas.append((ruta, resultado))

    monkeypatch.setitem(lambda_handler.TAREAS, "analisis_cv", ("/api/interno/resultados/analisis-cv", calcular))
    monkeypatch.setattr(lambda_handler, "entregar_resultado", entregar)

    respuesta = lambda_handler.handler({"Records": [_registro({"tipo": "analisis_cv", "tenant_id": "t1", "candidato_id": "c1"})]}, None)

    assert respuesta == {"batchItemFailures": []}
    assert entregas == [("/api/interno/resultados/analisis-cv", {"tenant_id": "t1", "candidato_id": "c1", "sin_texto": True})]


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tipo": "desconocido", "tenant_id": "t1"},
        {"tipo": "analisis_cv", "candidato_id": "c1"},  # sin tenant_id (DEC-016)
        "no es json",
    ],
    ids=["tipo-desconocido", "sin-tenant", "cuerpo-invalido"],
)
def test_un_mensaje_invalido_se_informa_para_reintento(cuerpo: Any) -> None:
    registro = {"messageId": "m-9", "body": cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo)}
    assert lambda_handler.handler({"Records": [registro]}, None) == {"batchItemFailures": [{"itemIdentifier": "m-9"}]}


def test_si_falla_el_calculo_solo_ese_mensaje_vuelve_a_la_cola(monkeypatch: pytest.MonkeyPatch) -> None:
    async def calcular(mensaje: dict[str, Any]) -> dict[str, Any]:
        if mensaje["candidato_id"] == "malo":
            raise RuntimeError("Gemini 503")
        return {"tenant_id": "t1", "candidato_id": mensaje["candidato_id"], "sin_texto": True}

    async def entregar(_ruta: str, _resultado: dict[str, Any]) -> None:
        return None

    monkeypatch.setitem(lambda_handler.TAREAS, "analisis_cv", ("/x", calcular))
    monkeypatch.setattr(lambda_handler, "entregar_resultado", entregar)
    registros = [
        _registro({"tipo": "analisis_cv", "tenant_id": "t1", "candidato_id": "bueno"}, "m-1"),
        _registro({"tipo": "analisis_cv", "tenant_id": "t1", "candidato_id": "malo"}, "m-2"),
    ]

    assert lambda_handler.handler({"Records": registros}, None) == {"batchItemFailures": [{"itemIdentifier": "m-2"}]}


async def test_la_entrega_va_firmada_y_un_error_del_backend_la_hace_fallar(monkeypatch: pytest.MonkeyPatch) -> None:
    vistas: list[httpx.Request] = []

    def backend(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(500)

    cliente_real = httpx.AsyncClient
    monkeypatch.setattr(settings, "backend_url_interno", "https://app.test/")
    monkeypatch.setattr(lambda_handler.httpx, "AsyncClient", lambda **kw: cliente_real(transport=httpx.MockTransport(backend), **kw))

    with pytest.raises(httpx.HTTPStatusError):
        await lambda_handler.entregar_resultado("/api/interno/resultados/analisis-cv", {"a": 1})

    peticion = vistas[0]
    assert str(peticion.url) == "https://app.test/api/interno/resultados/analisis-cv"
    assert verificar_firma(peticion.content, peticion.headers[CABECERA_MARCA], peticion.headers[CABECERA_FIRMA])


async def test_de_punta_a_punta_el_cv_queda_por_confirmar(
    client: TestClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mensaje de SQS -> cálculo (sin base) -> entrega firmada -> backend real -> cv_por_confirmar."""
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    db_session.add(area)
    await db_session.flush()
    vacante = Vacante(tenant_id=TENANT_ID, area_id=area.id, codigo="TI-2026-970", titulo="Backend", estado=EstadoVacante.ABIERTA)
    db_session.add(vacante)
    await db_session.flush()
    candidato = Candidato(
        tenant_id=TENANT_ID, vacante_id=vacante.id, nombre="Paolo", apellidos="Rivas", email="paolo.lambda@example.com",
        cv_url="https://vael-storage.s3.amazonaws.com/cvs/t/c/cv.pdf", estado=EstadoCandidato.CV_ANALIZANDO,
    )
    db_session.add(candidato)
    await db_session.commit()
    mensaje = analisis_cv.preparar_mensaje_analisis_cv(candidato, vacante, area)

    async def pdf_falso(_clave: str) -> bytes:
        return b"%PDF"

    async def gemini_falso(_prompt: str, model_name: str | None = None) -> dict[str, Any]:
        return {"criterios": CRITERIOS, "clasificacion": "recomendado", "resumen": "Bien"}

    def sin_base(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("El cálculo de la Lambda no debe abrir sesiones de base de datos (DEC-018)")

    monkeypatch.setattr(analisis_cv, "descargar_archivo", pdf_falso)
    monkeypatch.setattr(analisis_cv, "extraer_texto_pdf", lambda _b: "Python FastAPI")
    monkeypatch.setattr(analisis_cv, "consultar_gemini_json", gemini_falso)
    monkeypatch.setattr(analisis_cv, "async_session_factory", sin_base)
    # La entrega llega a la aplicación real (con las sesiones de prueba del fixture `client`)
    cliente_real = httpx.AsyncClient
    monkeypatch.setattr(settings, "backend_url_interno", "http://backend")
    monkeypatch.setattr(
        lambda_handler.httpx, "AsyncClient", lambda **kw: cliente_real(transport=httpx.ASGITransport(app=app), **kw)
    )

    await lambda_handler.procesar_mensaje(json.loads(json.dumps(mensaje)))

    await db_session.refresh(candidato)
    assert candidato.estado is EstadoCandidato.CV_POR_CONFIRMAR
    assert candidato.score_cv == 70
