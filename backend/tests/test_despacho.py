"""Pruebas del despachador único de tareas (DEC-016, DEV-C-13, modo en proceso)."""
import inspect
import json
import logging
from typing import Any

import pytest

from app.core import despacho
from app.core.database import con_tenant, tenant_fijado
from app.core.despacho import TipoTarea, despachar_tarea
from app.routers import candidatos, entrevista, publico


@pytest.fixture
def ejecutadas(monkeypatch: pytest.MonkeyPatch) -> list[tuple[TipoTarea, dict[str, Any]]]:
    """Reemplaza los manejadores reales por uno que registra lo que recibe."""
    registro: list[tuple[TipoTarea, dict[str, Any]]] = []

    def manejador_falso(tipo: TipoTarea) -> despacho.Manejador:
        async def ejecutar(payload: dict[str, Any]) -> None:
            registro.append((tipo, payload))

        return ejecutar

    monkeypatch.setattr(despacho, "_manejador", manejador_falso)
    return registro


async def test_ejecuta_la_tarea_con_su_payload(ejecutadas: list[Any]) -> None:
    """La tarea corre en proceso con el payload recibido."""
    payload = {"tenant_id": "t1", "candidato_id": "c1"}
    tarea = await despachar_tarea(TipoTarea.ANALISIS_CV, payload)
    await tarea
    assert ejecutadas == [(TipoTarea.ANALISIS_CV, payload)]


async def test_acepta_el_tipo_como_texto(ejecutadas: list[Any]) -> None:
    """El tipo puede llegar como texto (por ejemplo, desde un mensaje de SQS)."""
    tarea = await despachar_tarea("analisis_entrevista", {"tenant_id": "t1", "entrevista_id": "e1"})
    await tarea
    assert ejecutadas[0][0] is TipoTarea.ANALISIS_ENTREVISTA


@pytest.mark.parametrize(
    ("tipo", "payload"),
    [
        (TipoTarea.ANALISIS_CV, {"candidato_id": "c1"}),
        (TipoTarea.ANALISIS_CV, {"tenant_id": "t1"}),
        (TipoTarea.ANALISIS_ENTREVISTA, {"tenant_id": "t1", "candidato_id": "c1"}),
    ],
)
async def test_exige_tenant_e_identificador(ejecutadas: list[Any], tipo: TipoTarea, payload: dict[str, Any]) -> None:
    """Sin tenant_id o sin el identificador del tipo, el despacho se rechaza (DEC-016, punto 6)."""
    with pytest.raises(ValueError):
        await despachar_tarea(tipo, payload)
    assert ejecutadas == []


async def test_exige_payload_serializable(ejecutadas: list[Any]) -> None:
    """El payload debe poder viajar como JSON en un mensaje de SQS."""
    with pytest.raises(ValueError, match="serializable"):
        await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": "t1", "candidato_id": "c1", "objeto": object()})


async def test_rechaza_tipos_desconocidos() -> None:
    """Un tipo fuera del catálogo no se despacha."""
    with pytest.raises(ValueError):
        await despachar_tarea("tipo_inexistente", {"tenant_id": "t1"})


async def test_una_falla_se_registra_sin_propagarse(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Si la tarea falla, queda en el log con su tenant y no tumba el proceso."""

    def manejador_que_falla(_tipo: TipoTarea) -> despacho.Manejador:
        async def ejecutar(_payload: dict[str, Any]) -> None:
            raise RuntimeError("falla simulada")

        return ejecutar

    monkeypatch.setattr(despacho, "_manejador", manejador_que_falla)
    with caplog.at_level(logging.ERROR, logger="app.core.despacho"):
        tarea = await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": "t1", "candidato_id": "c1"})
        await tarea
    assert any("falló" in r.getMessage() for r in caplog.records)


def test_manejadores_reales_existen_para_cada_tipo() -> None:
    """Cada tipo del catálogo resuelve a una función ejecutable."""
    for tipo in TipoTarea:
        assert callable(despacho._manejador(tipo))


@pytest.mark.parametrize("modulo", [candidatos, publico, entrevista])
def test_los_routers_de_analisis_no_usan_background_tasks(modulo: Any) -> None:
    """Los análisis se despachan con despachar_tarea, nunca con BackgroundTasks (DEC-016)."""
    codigo = inspect.getsource(modulo)
    assert "BackgroundTasks" not in codigo
    assert "despachar_tarea" in codigo


async def test_la_tarea_usa_el_tenant_del_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """La tarea fija el tenant del mensaje (DEC-016 punto 6), no el de la petición que la despachó."""
    vistos: list[str | None] = []

    def manejador_que_observa(tipo: TipoTarea) -> despacho.Manejador:
        async def ejecutar(payload: dict[str, Any]) -> None:
            vistos.append(tenant_fijado())

        return ejecutar

    monkeypatch.setattr(despacho, "_manejador", manejador_que_observa)
    with con_tenant("tenant-de-la-peticion"):
        tarea = await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": "tenant-del-mensaje", "candidato_id": "c-1"})
    await tarea

    assert vistos == ["tenant-del-mensaje"]


# --- Modo sqs (HU-23): el backend prepara el mensaje y lo publica; no analiza en proceso ---


@pytest.fixture
def modo_sqs(monkeypatch: pytest.MonkeyPatch, db_engine: Any) -> list[tuple[str, dict[str, Any]]]:
    """Activa el modo sqs con colas de prueba y registra lo que se publicaría en SQS."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    from app.core.config import settings
    from app.core.database import CLAVE_TENANT
    from app.services import aws_services

    publicados: list[tuple[str, dict[str, Any]]] = []

    async def encolar_falso(cola_url: str, mensaje: dict[str, Any], delay_segundos: int = 0) -> str:
        json.dumps(mensaje)  # debe poder viajar como cuerpo de SQS
        publicados.append((cola_url, mensaje))
        return "mensaje-1"

    def no_en_proceso(_tipo: TipoTarea) -> despacho.Manejador:
        raise AssertionError("En modo sqs la tarea no debe correr en proceso")

    monkeypatch.setattr(settings, "despacho_modo", "sqs")
    monkeypatch.setattr(settings, "sqs_url_analisis_cv", "https://sqs.test/vael-analisis-cv")
    monkeypatch.setattr(settings, "sqs_url_analisis_entrevista", "https://sqs.test/vael-analisis-entrevista")
    monkeypatch.setattr(aws_services, "encolar_tarea", encolar_falso)
    monkeypatch.setattr(despacho, "_manejador", no_en_proceso)
    monkeypatch.setattr(
        despacho, "sesion_con_tenant", lambda tenant_id: AsyncSession(db_engine, expire_on_commit=False, info={CLAVE_TENANT: tenant_id})
    )
    return publicados


async def test_en_modo_sqs_publica_el_mensaje_completo_del_cv(modo_sqs: list[Any], db_session: Any) -> None:
    """El mensaje lleva todo lo que el cálculo necesita, para que la Lambda no consulte la base (DEC-018)."""
    from app.models.area import Area
    from app.models.candidato import Candidato
    from app.models.vacante import EstadoVacante, Vacante
    from tests.conftest import TENANT_ID

    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI", instruccion_ia="Prioriza APIs")
    db_session.add(area)
    await db_session.flush()
    vacante = Vacante(
        tenant_id=TENANT_ID, area_id=area.id, codigo="TI-2026-960", titulo="Backend Python",
        estado=EstadoVacante.ABIERTA, requisitos="Python", habilidades=["FastAPI"],
    )
    db_session.add(vacante)
    await db_session.flush()
    candidato = Candidato(
        tenant_id=TENANT_ID, vacante_id=vacante.id, nombre="Kevin", apellidos="Huamán", email="kevin.sqs@example.com",
        cv_url="https://vael-storage.s3.amazonaws.com/cvs/tenant/c1/cv.pdf",
    )
    db_session.add(candidato)
    await db_session.commit()

    tarea = await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": TENANT_ID, "candidato_id": candidato.id})
    await tarea

    assert len(modo_sqs) == 1
    cola, mensaje = modo_sqs[0]
    assert cola == "https://sqs.test/vael-analisis-cv"
    assert mensaje["tipo"] == "analisis_cv"
    assert mensaje["tenant_id"] == TENANT_ID
    assert mensaje["candidato_id"] == candidato.id
    assert mensaje["cv_key"] == "cvs/tenant/c1/cv.pdf"
    assert mensaje["vacante"]["titulo"] == "Backend Python"
    assert mensaje["vacante"]["habilidades"] == ["FastAPI"]
    assert mensaje["vacante"]["instruccion_area"] == "Prioriza APIs"


async def test_en_modo_sqs_no_publica_si_el_registro_no_existe(modo_sqs: list[Any]) -> None:
    tarea = await despachar_tarea(TipoTarea.ANALISIS_ENTREVISTA, {"tenant_id": "tenant-x", "entrevista_id": "no-existe"})
    await tarea
    assert modo_sqs == []


def test_el_modo_sqs_exige_las_colas() -> None:
    from app.core.config import Settings

    with pytest.raises(ValueError, match="SQS_URL"):
        Settings(despacho_modo="sqs", sqs_url_analisis_cv="", sqs_url_analisis_entrevista="")
