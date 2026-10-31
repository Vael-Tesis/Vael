"""Pruebas del dashboard de métricas (RF-A-19, HU-20, doc 14) — DEV-A-10.

Cubren: aislamiento por tenant (DEC-010), las cifras agregadas (estado de vacantes y
candidatos, recomendaciones pendientes por etapa), el cálculo exacto de OE1 (minutos
promedio de revisión) y M-02 (tasa de concordancia) sobre datos controlados, el filtro
`desde`/`hasta`, y la coherencia de las cifras contra los datos semilla del doc 13.
"""
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import CLAVE_TENANT
from app.core.security import create_access_token
from app.models.area import Area
from app.models.candidato import Candidato, EstadoCandidato
from app.models.decision import DecisionCandidato, EtapaDecision, TipoDecision
from app.models.usuario import RolUsuario, Usuario
from app.models.vacante import EstadoVacante, Vacante
from app.scripts import crear_empresa as alta
from app.scripts import semillas
from app.services import correos
from tests.conftest import TENANT_ID, TENANT_ID_OTRO
from tests.test_decisiones import _candidato, _vacante

PASSWORD_SEMILLA = "Semilla-Prueba-2026"


@pytest.fixture
def abrir(db_engine: AsyncEngine) -> alta.AbrirSesion:
    """Sesiones vael_app contra la base de prueba, como las que abre el script en producción."""
    return lambda tenant_id: AsyncSession(db_engine, expire_on_commit=False, info={CLAVE_TENANT: tenant_id})


@pytest.fixture
def con_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "seed_password", PASSWORD_SEMILLA)

    async def enviar_falso(destinatario: str, asunto: str, html: str) -> None:
        return None

    monkeypatch.setattr(correos, "_enviar_correo", enviar_falso)


def _ruta(**params: Any) -> str:
    query = "&".join(f"{clave}={valor}" for clave, valor in params.items() if valor is not None)
    return f"/api/metricas/dashboard?{query}" if query else "/api/metricas/dashboard"


async def _usuario(db: AsyncSession, tenant_id: str) -> Usuario:
    usuario = Usuario(
        tenant_id=tenant_id, nombre="Test", apellidos="Admin", email=f"admin@{tenant_id}.vael",
        password_hash="no-usado-en-estos-tests", rol=RolUsuario.ADMIN,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def _vacante_de(db: AsyncSession, tenant_id: str, sufijo: str) -> Vacante:
    """Como `_vacante` de test_decisiones, pero parametrizada por tenant (para el tenant ajeno;
    `_vacante` siempre usa TENANT_ID, así que no sirve para crear datos de otra empresa)."""
    area = Area(tenant_id=tenant_id, nombre=f"Área {sufijo}", codigo_corto=f"A{sufijo}")
    db.add(area)
    await db.flush()
    vacante = Vacante(
        tenant_id=tenant_id, area_id=area.id, codigo=f"{sufijo}-2026-001", titulo=f"Vacante {sufijo}",
        estado=EstadoVacante.ABIERTA, score_cv_minimo=60, nota_minima_examen=13,
    )
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante


async def _candidato_de(db: AsyncSession, tenant_id: str, vacante: Vacante, estado: EstadoCandidato, sufijo: str) -> Candidato:
    candidato = Candidato(
        tenant_id=tenant_id, vacante_id=vacante.id, nombre="Test", apellidos=f"Candidato {sufijo}",
        email=f"candidato{sufijo}@example.com", estado=estado,
    )
    db.add(candidato)
    await db.commit()
    await db.refresh(candidato)
    return candidato


def _decision(
    tenant_id: str, candidato_id: str, decidido_por: str, etapa: EtapaDecision,
    revision_inicio: datetime | None, decidido_en: datetime, coincide: bool | None,
) -> DecisionCandidato:
    return DecisionCandidato(
        tenant_id=tenant_id, candidato_id=candidato_id, etapa=etapa, decision=TipoDecision.AVANZAR,
        coincide_con_ia=coincide, decidido_por=decidido_por, revision_inicio=revision_inicio, decidido_en=decidido_en,
    )


# --- Aislamiento por tenant (DEC-010) ------------------------------------------------------


async def test_una_empresa_no_ve_las_metricas_de_otra(
    client: TestClient, db_session: AsyncSession, db_engine: AsyncEngine
) -> None:
    """Candidatos y decisiones del tenant ajeno no deben aparecer en ningún conteo."""
    admin = await _usuario(db_session, TENANT_ID)
    vacante = await _vacante(db_session)
    propio = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, sufijo="propio")
    db_session.add(_decision(TENANT_ID, propio.id, admin.id, EtapaDecision.CV, None, propio.fecha_postulacion, True))
    await db_session.commit()

    async with AsyncSession(db_engine, info={CLAVE_TENANT: TENANT_ID_OTRO}, expire_on_commit=False) as otra:
        admin_ajeno = await _usuario(otra, TENANT_ID_OTRO)
        vacante_ajena = await _vacante_de(otra, TENANT_ID_OTRO, "ajena")
        ajeno = await _candidato_de(otra, TENANT_ID_OTRO, vacante_ajena, EstadoCandidato.ENTREVISTA_REALIZADA, "ajeno")
        otra.add(_decision(TENANT_ID_OTRO, ajeno.id, admin_ajeno.id, EtapaDecision.CV, None, ajeno.fecha_postulacion, False))
        await otra.commit()

    token = await create_access_token(admin.id, TENANT_ID, admin.rol.value)
    respuesta = client.get(_ruta(), headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["candidatos_por_estado"]["cv_por_confirmar"] == 1
    assert cuerpo["candidatos_por_estado"]["entrevista_realizada"] == 0  # el ajeno no cuenta
    assert cuerpo["recomendaciones_pendientes_por_etapa"] == {"cv": 1, "examen": 0, "entrevista": 0}
    assert cuerpo["tasa_concordancia"] == 100.0  # solo la decisión propia (True); la ajena (False) no cuenta


# --- OE1 (minutos promedio de revisión) y M-02 (tasa de concordancia) ----------------------


async def test_oe1_y_m02_se_calculan_sobre_las_decisiones_del_tenant(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Promedio exacto de minutos y porcentaje exacto de concordancia, con datos controlados."""
    admin = await _usuario(db_session, TENANT_ID)
    vacante = await _vacante(db_session)
    c1 = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, sufijo="1")
    c2 = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, sufijo="2")
    c3 = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, sufijo="3")
    base = datetime(2026, 10, 1, 12, 0, 0)

    db_session.add_all([
        # 10 minutos de revisión, coincide con la IA
        _decision(TENANT_ID, c1.id, admin.id, EtapaDecision.CV, base, base + timedelta(minutes=10), True),
        # 20 minutos de revisión, no coincide (justificación aparte, no afecta este cálculo)
        _decision(TENANT_ID, c2.id, admin.id, EtapaDecision.EXAMEN, base, base + timedelta(minutes=20), False),
        # sin revision_inicio: no cuenta para el promedio de minutos, pero sí para la concordancia
        _decision(TENANT_ID, c3.id, admin.id, EtapaDecision.CV, None, base, True),
    ])
    await db_session.commit()

    token = await create_access_token(admin.id, TENANT_ID, admin.rol.value)
    respuesta = client.get(_ruta(), headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["minutos_promedio_revision"] == 15.0  # promedio de 10 y 20 (el tercero no cuenta)
    assert cuerpo["tasa_concordancia"] == 66.67  # 2 de 3 coinciden, redondeado a 2 decimales


async def test_sin_decisiones_las_metricas_de_decisiones_quedan_nulas(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Sin ninguna decisión, OE1 y M-02 son null en vez de cero o un error de división."""
    admin = await _usuario(db_session, TENANT_ID)

    token = await create_access_token(admin.id, TENANT_ID, admin.rol.value)
    respuesta = client.get(_ruta(), headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["minutos_promedio_revision"] is None
    assert cuerpo["tasa_concordancia"] is None
    assert cuerpo["postulaciones_por_dia"] == []
    assert cuerpo["recomendaciones_pendientes_por_etapa"] == {"cv": 0, "examen": 0, "entrevista": 0}
    assert all(cantidad == 0 for cantidad in cuerpo["vacantes_por_estado"].values())
    assert all(cantidad == 0 for cantidad in cuerpo["candidatos_por_estado"].values())


async def test_desde_y_hasta_acotan_postulaciones_y_decisiones(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Una decisión fuera del rango no debe entrar en el promedio ni en la concordancia."""
    admin = await _usuario(db_session, TENANT_ID)
    vacante = await _vacante(db_session)
    dentro = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, sufijo="dentro")
    fuera = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, sufijo="fuera")

    db_session.add_all([
        _decision(TENANT_ID, dentro.id, admin.id, EtapaDecision.CV, datetime(2026, 10, 15), datetime(2026, 10, 15, 0, 30), True),
        _decision(TENANT_ID, fuera.id, admin.id, EtapaDecision.CV, datetime(2026, 9, 1), datetime(2026, 9, 1, 1, 0), False),
    ])
    await db_session.commit()

    token = await create_access_token(admin.id, TENANT_ID, admin.rol.value)
    respuesta = client.get(_ruta(desde="2026-10-01", hasta="2026-10-31"), headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["minutos_promedio_revision"] == 30.0
    assert cuerpo["tasa_concordancia"] == 100.0
    # Las fotografías de estado actual no se acotan por fecha (siguen viendo a ambos candidatos)
    assert cuerpo["candidatos_por_estado"]["cv_por_confirmar"] == 2


# --- Coherencia con los datos semilla (doc 13) ----------------------------------------------


async def test_cifras_coherentes_con_los_datos_semilla(
    client: TestClient, abrir: alta.AbrirSesion, con_password: None
) -> None:
    """Contra los ocho candidatos de TI-2026-001 (doc 13): siete con entrevista realizada y
    pendiente de decisión, uno con el examen aprobado y sin entrevista (proceso incompleto)."""
    await semillas.cargar(abrir, generar_pdfs=False)

    login = client.post("/api/auth/login", json={"email": "admin@andina.example.com", "password": PASSWORD_SEMILLA})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    respuesta = client.get(_ruta(), headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["vacantes_por_estado"] == {"borrador": 1, "abierta": 3, "pausada": 0, "cerrada": 0}
    assert cuerpo["candidatos_por_estado"]["entrevista_realizada"] == len(semillas.CANDIDATOS_TI_COMPLETOS)
    assert cuerpo["candidatos_por_estado"]["examen_aprobado"] == 1  # Jorge Salcedo Peña, incompleto
    assert cuerpo["recomendaciones_pendientes_por_etapa"] == {
        "cv": 0, "examen": 0, "entrevista": len(semillas.CANDIDATOS_TI_COMPLETOS),
    }
    assert sum(p["cantidad"] for p in cuerpo["postulaciones_por_dia"]) == len(semillas.CANDIDATOS_TI_COMPLETOS) + 1
    # Las semillas no fijan revision_inicio (DEV-A-07): nada que promediar para OE1
    assert cuerpo["minutos_promedio_revision"] is None
    # Todas las decisiones de CV y examen coinciden con la recomendación (umbrales superados)
    assert cuerpo["tasa_concordancia"] == 100.0
