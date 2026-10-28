"""Registro de candidatos y CV que fallan (DEV-A-05, HU-11): carga masiva con reporte de fallidos,
registro manual con validación del PDF, CV escaneado a revisión manual y semáforo en la bandeja."""
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.candidato import ClasificacionIA, EstadoCandidato
from app.models.evaluacion import SemaforoExamen
from app.routers import candidatos as router_candidatos
from app.routers import publico as router_publico
from app.scripts import generar_cvs
from app.services import analisis_cv
from tests.test_decisiones import _candidato, _examen, _vacante

CV_VALIDO = generar_cvs.pdf_de_texto("Ana Ruiz\nDesarrolladora Python con 4 años de experiencia")
CV_DANADO = generar_cvs.pdf_danado("Ana Ruiz\nDesarrolladora Python")
CV_ESCANEADO = generar_cvs.pdf_escaneado()


@pytest.fixture
def s3_y_despacho(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    """S3 y el despachador en memoria: guarda lo subido y las tareas, sin ejecutar el análisis."""
    registro: dict[str, list[Any]] = {"subidos": [], "tareas": []}

    async def subir_falso(contenido: bytes, clave: str, tipo: str) -> str:
        registro["subidos"].append(clave)
        return f"https://s3.example.com/{clave}"

    async def despachar_falso(tipo: Any, payload: dict[str, Any]) -> None:
        registro["tareas"].append(payload)

    monkeypatch.setattr(router_candidatos, "subir_archivo", subir_falso)
    monkeypatch.setattr(router_candidatos, "despachar_tarea", despachar_falso)
    return registro


async def test_la_carga_masiva_informa_los_archivos_que_fallaron(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, s3_y_despacho: dict[str, list[Any]]
) -> None:
    vacante = await _vacante(db_session)
    archivos = [
        ("archivos", ("ana_ruiz.pdf", CV_VALIDO, "application/pdf")),
        ("archivos", ("escaneado.pdf", CV_ESCANEADO, "application/pdf")),
        ("archivos", ("danado.pdf", CV_DANADO, "application/pdf")),
        ("archivos", ("cv.docx", b"PK\x03\x04 no es pdf", "application/octet-stream")),
        ("archivos", ("vacio.pdf", b"", "application/pdf")),
    ]

    respuesta = client.post("/api/candidatos/carga-masiva", data={"vacante_id": vacante.id}, files=archivos, headers=admin_headers)

    assert respuesta.status_code == 202, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["creados"] == 2  # el escaneado se acepta: va a revisión manual
    assert {f["nombre"]: f["motivo"] for f in cuerpo["fallidos"]} == {
        "danado.pdf": "El PDF está dañado o no se puede leer",
        "cv.docx": "No es un PDF",
        "vacio.pdf": "El archivo está vacío",
    }
    assert len(s3_y_despacho["subidos"]) == 2 and len(s3_y_despacho["tareas"]) == 2


async def test_un_error_de_s3_se_reporta_como_fallido(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    vacante = await _vacante(db_session)

    async def subir_que_falla(*_args: Any) -> str:
        raise RuntimeError("NoCredentialsError")

    monkeypatch.setattr(router_candidatos, "subir_archivo", subir_que_falla)

    masiva = client.post(
        "/api/candidatos/carga-masiva",
        data={"vacante_id": vacante.id},
        files=[("archivos", ("ana.pdf", CV_VALIDO, "application/pdf"))],
        headers=admin_headers,
    )
    assert masiva.json()["creados"] == 0
    assert masiva.json()["fallidos"][0]["motivo"].startswith("No se pudo guardar")

    manual = client.post(
        "/api/candidatos",
        data={"vacante_id": vacante.id, "nombre": "Ana", "apellidos": "Ruiz", "email": "ana@example.com"},
        files={"cv": ("ana.pdf", CV_VALIDO, "application/pdf")},
        headers=admin_headers,
    )
    assert manual.status_code == 502


async def test_el_registro_manual_rechaza_un_pdf_danado(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, s3_y_despacho: dict[str, list[Any]]
) -> None:
    vacante = await _vacante(db_session)
    datos = {"vacante_id": vacante.id, "nombre": "Ana", "apellidos": "Ruiz", "email": "ana@example.com"}

    danado = client.post("/api/candidatos", data=datos, files={"cv": ("cv.pdf", CV_DANADO, "application/pdf")}, headers=admin_headers)
    valido = client.post("/api/candidatos", data=datos, files={"cv": ("cv.pdf", CV_VALIDO, "application/pdf")}, headers=admin_headers)

    assert danado.status_code == 422 and "dañado" in danado.json()["detail"]
    assert valido.status_code == 201
    assert s3_y_despacho["tareas"] == [{"tenant_id": valido.json()["tenant_id"], "candidato_id": valido.json()["id"]}]


async def test_un_cv_escaneado_va_a_revision_manual_sin_llamar_a_la_ia(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_ANALIZANDO, score_cv=None)
    candidato.cv_url = "https://s3.example.com/escaneado.pdf"

    async def pdf_falso(_url: str) -> bytes:
        return CV_ESCANEADO

    async def gemini_prohibido(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("Un CV sin texto no se envía a la IA")

    monkeypatch.setattr(analisis_cv, "_descargar_pdf", pdf_falso)
    monkeypatch.setattr(analisis_cv, "consultar_gemini_json", gemini_prohibido)

    await analisis_cv.analizar_cv(candidato, vacante, None, db_session)

    assert candidato.estado is EstadoCandidato.CV_POR_CONFIRMAR
    assert candidato.clasificacion_ia is ClasificacionIA.REQUIERE_REVISION
    assert candidato.score_cv is None and "revisión manual" in (candidato.resumen_ia or "")


async def test_la_bandeja_muestra_el_semaforo_del_examen(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_POR_CONFIRMAR)
    examen = await _examen(db_session, candidato, 15.0)
    examen.semaforo = SemaforoExamen.ROJO
    db_session.add(examen)
    await db_session.commit()

    bandeja = client.get("/api/candidatos/por-confirmar", headers=admin_headers).json()

    assert [(i["etapa"], i["semaforo"]) for i in bandeja] == [("examen", "rojo")]


async def test_la_postulacion_publica_valida_el_cv_y_reporta_el_error_de_s3(
    client: TestClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Observación de TST-A-01: sin S3 la postulación respondía 500 sin mensaje."""
    vacante = await _vacante(db_session)
    ruta = f"/api/publico/postular/{vacante.codigo}/enviar"
    datos = {"nombre": "Ana", "apellidos": "Ruiz", "email": "ana@example.com"}
    tareas: list[dict[str, Any]] = []

    async def subir_que_falla(*_args: Any) -> str:
        raise RuntimeError("NoCredentialsError")

    async def despachar_falso(tipo: Any, payload: dict[str, Any]) -> None:
        tareas.append(payload)

    monkeypatch.setattr(router_publico, "subir_archivo", subir_que_falla)
    monkeypatch.setattr(router_publico, "despachar_tarea", despachar_falso)

    danado = client.post(ruta, data=datos, files={"cv": ("cv.pdf", CV_DANADO, "application/pdf")})
    assert danado.status_code == 422
    assert danado.json()["detail"] == "El PDF está dañado o no se puede leer"

    sin_s3 = client.post(ruta, data=datos, files={"cv": ("cv.pdf", CV_VALIDO, "application/pdf")})
    assert sin_s3.status_code == 502
    assert sin_s3.json()["detail"] == "No se pudo guardar el CV; intenta de nuevo"
    assert tareas == []

    async def subir_falso(_contenido: bytes, clave: str, _tipo: str) -> str:
        return f"https://s3.example.com/{clave}"

    monkeypatch.setattr(router_publico, "subir_archivo", subir_falso)
    ok = client.post(ruta, data=datos, files={"cv": ("cv.pdf", CV_VALIDO, "application/pdf")})
    assert ok.status_code == 201, ok.text
    assert tareas == [{"tenant_id": vacante.tenant_id, "candidato_id": ok.json()["candidato_id"]}]
