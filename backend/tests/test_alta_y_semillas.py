"""Pruebas del alta de empresas (DEC-015) y de los datos semilla del doc 13 — DEV-C-03."""
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings
from app.core.database import CLAVE_TENANT
from app.models.area import Area
from app.models.candidato import Candidato, NotaCandidato
from app.models.decision import DecisionCandidato
from app.models.entrevista import DimensionEvaluacion, EntrevistaIA, PlantillaEvaluacion
from app.models.evaluacion import Examen
from app.models.usuario import Empresa, Usuario
from app.models.vacante import Vacante
from app.scripts import crear_empresa as alta
from app.scripts import generar_cvs, semillas
from app.services import correos
from app.services.analisis_cv import extraer_texto_pdf
from tests.conftest import TENANT_ID
from tests.test_invariante_decisiones import _indicador_oe3

PASSWORD_SEMILLA = "Semilla-Prueba-2026"


@pytest.fixture
def abrir(db_engine: AsyncEngine) -> alta.AbrirSesion:
    """Sesiones vael_app contra la base de prueba, como las que abre el script en producción."""
    return lambda tenant_id: AsyncSession(db_engine, expire_on_commit=False, info={CLAVE_TENANT: tenant_id})


@pytest.fixture
def credenciales(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Captura (correo, contraseña temporal) en lugar de enviar el correo de credenciales."""
    enviadas: list[tuple[str, str]] = []

    async def enviar_falso(usuario: Usuario, password_temporal: str) -> None:
        enviadas.append((usuario.email, password_temporal))

    monkeypatch.setattr(alta, "correo_credenciales_usuario", enviar_falso)
    return enviadas


async def _contar(system_engine: AsyncEngine, modelo: type[SQLModel]) -> int:
    async with AsyncSession(system_engine) as db:
        return (await db.exec(select(func.count()).select_from(modelo))).one()


def _login(client: TestClient, email: str, password: str) -> Any:
    return client.post("/api/auth/login", json={"email": email, "password": password})


# --- Alta de empresa (DEC-015) -------------------------------------------------------------


async def test_crea_la_empresa_y_su_administrador_puede_iniciar_sesion(
    client: TestClient, abrir: alta.AbrirSesion, credenciales: list[tuple[str, str]]
) -> None:
    resultado = await alta.crear_empresa(
        "Empresa Uno S.A.C.", "Admin@Uno.example.com", email_contacto="datos@uno.example.com", abrir_sesion=abrir
    )

    assert resultado.empresa_creada and resultado.administrador_creado
    assert resultado.empresa.email_contacto == "datos@uno.example.com"
    assert resultado.administrador.tenant_id == resultado.tenant_id
    assert [email for email, _ in credenciales] == ["admin@uno.example.com"]
    password = credenciales[0][1]
    assert len(password) >= 12

    respuesta = _login(client, "admin@uno.example.com", password)
    assert respuesta.status_code == 200, respuesta.text


async def test_ejecutarlo_dos_veces_no_duplica(
    abrir: alta.AbrirSesion, credenciales: list[tuple[str, str]], system_engine: AsyncEngine
) -> None:
    primera = await alta.crear_empresa("Empresa Dos S.A.C.", "admin@dos.example.com", abrir_sesion=abrir)
    segunda = await alta.crear_empresa("  empresa   DOS s.a.c. ", "admin@dos.example.com", abrir_sesion=abrir)

    assert segunda.tenant_id == primera.tenant_id
    assert not segunda.empresa_creada and not segunda.administrador_creado
    assert len(credenciales) == 1
    assert await _contar(system_engine, Empresa) == 1
    assert await _contar(system_engine, Usuario) == 1


async def test_el_administrador_solo_ve_su_empresa(
    client: TestClient, abrir: alta.AbrirSesion, credenciales: list[tuple[str, str]], db_session: AsyncSession
) -> None:
    db_session.add(Area(tenant_id=TENANT_ID, nombre="Área ajena", codigo_corto="AJ"))
    await db_session.commit()
    await alta.crear_empresa("Empresa Tres S.A.C.", "admin@tres.example.com", abrir_sesion=abrir)

    token = _login(client, "admin@tres.example.com", credenciales[0][1]).json()["access_token"]
    areas = client.get("/api/areas", headers={"Authorization": f"Bearer {token}"})

    assert areas.status_code == 200
    assert areas.json() == []


async def test_un_correo_de_otra_empresa_no_crea_nada(
    abrir: alta.AbrirSesion, credenciales: list[tuple[str, str]], system_engine: AsyncEngine
) -> None:
    await alta.crear_empresa("Empresa Cuatro S.A.C.", "compartido@example.com", abrir_sesion=abrir)

    with pytest.raises(alta.ErrorAlta, match="otra empresa"):
        await alta.crear_empresa("Empresa Cinco S.A.C.", "compartido@example.com", abrir_sesion=abrir)

    assert await _contar(system_engine, Empresa) == 1
    assert len(credenciales) == 1


def test_el_tenant_no_depende_de_mayusculas_ni_espacios() -> None:
    assert alta.tenant_de("Andina  Servicios S.A.C.") == alta.tenant_de("andina servicios s.a.c.")
    assert alta.tenant_de("Andina Servicios S.A.C.") != alta.tenant_de("Pacífico Logística S.A.C.")


# --- Semillas (doc 13) ---------------------------------------------------------------------


@pytest.fixture
def con_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "seed_password", PASSWORD_SEMILLA)

    async def enviar_falso(destinatario: str, asunto: str, html: str) -> None:
        return None

    monkeypatch.setattr(correos, "_enviar_correo", enviar_falso)


@pytest.fixture
def con_password_y_registro_de_correos(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Como `con_password`, pero registra los destinatarios en lugar de descartarlos, para
    comprobar que las semillas no envían ninguno (corrección de DEV-A-07)."""
    monkeypatch.setattr(settings, "seed_password", PASSWORD_SEMILLA)
    enviados: list[str] = []

    async def enviar_falso(destinatario: str, asunto: str, html: str) -> None:
        enviados.append(destinatario)

    monkeypatch.setattr(correos, "_enviar_correo", enviar_falso)
    return enviados


async def test_las_semillas_son_idempotentes(
    abrir: alta.AbrirSesion, con_password: None, system_engine: AsyncEngine
) -> None:
    """Dos ejecuciones dejan exactamente los datos del doc 13."""
    await semillas.cargar(abrir, generar_pdfs=False)
    resumen = await semillas.cargar(abrir, generar_pdfs=False)

    esperados = {
        Empresa: 2,
        Usuario: 7,  # A: admin, reclutador, evaluador, gerente, inactivo · B: admin, reclutador
        Area: 4,
        PlantillaEvaluacion: 4,
        DimensionEvaluacion: 17,  # 5 + 4 + 4 + 4 (doc 05)
        Vacante: 5,
        # B: 3 candidatos de siempre · A: 7 con proceso completo + 1 con examen sin entrevista
        # en TI-2026-001, más candidatos que top_candidatos_finalistas para el ranking (DEC-022)
        Candidato: 3 + len(semillas.CANDIDATOS_TI_COMPLETOS) + 1,
        NotaCandidato: 1,
        Examen: 1 + len(semillas.CANDIDATOS_TI_COMPLETOS) + 1,
        EntrevistaIA: len(semillas.CANDIDATOS_TI_COMPLETOS),
        # B: 1 decisión (CV) · A: CV + examen por cada candidato de TI-2026-001
        DecisionCandidato: 1 + (len(semillas.CANDIDATOS_TI_COMPLETOS) + 1) * 2,
    }
    for modelo, cantidad in esperados.items():
        assert await _contar(system_engine, modelo) == cantidad, modelo.__name__
    assert resumen[semillas.EMPRESA_A]["vacantes"] == ["TI-2026-001", "VEN-2026-001", "OPE-2026-001", "TI-2026-002"]


async def test_las_semillas_no_envian_correos(
    abrir: alta.AbrirSesion, con_password_y_registro_de_correos: list[str]
) -> None:
    """Las decisiones de CV y examen que avanzan a los candidatos (empresa B y TI-2026-001) no
    deben disparar correos reales: encender el entorno en AWS enviaría correos por SES a
    direcciones @example.com (corrección de DEV-A-07, DEC-009, DEC-013)."""
    await semillas.cargar(abrir, generar_pdfs=False)

    assert con_password_y_registro_de_correos == []


async def test_los_usuarios_semilla_inician_sesion_y_cada_empresa_ve_lo_suyo(
    client: TestClient, abrir: alta.AbrirSesion, con_password: None
) -> None:
    """El reclutador de A no ve los candidatos de B; el admin de B ve su bandeja (CV y examen)."""
    await semillas.cargar(abrir, generar_pdfs=False)

    login_a = _login(client, "reclutador@andina.example.com", PASSWORD_SEMILLA)
    login_b = _login(client, "admin@pacifico.example.com", PASSWORD_SEMILLA)
    inactivo = _login(client, "inactivo@andina.example.com", PASSWORD_SEMILLA)
    assert login_a.status_code == 200 and login_b.status_code == 200
    assert inactivo.status_code in (401, 403)

    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    candidatos_a = client.get("/api/candidatos", headers=headers_a).json()
    correos_b = {correo for _, _, correo, _, _ in semillas.CANDIDATOS_B}
    assert len(candidatos_a) == len(semillas.CANDIDATOS_TI_COMPLETOS) + 1
    assert not (correos_b & {c["email"] for c in candidatos_a})
    bandeja = client.get("/api/candidatos/por-confirmar", headers=headers_b).json()
    assert sorted(item["etapa"] for item in bandeja) == ["cv", "cv", "examen"]


async def test_las_semillas_respetan_el_invariante_del_oe3(
    abrir: alta.AbrirSesion, con_password: None
) -> None:
    """El candidato de B con examen pasó por una decisión humana registrada."""
    tenant_b = alta.tenant_de(semillas.EMPRESA_B)
    await semillas.cargar(abrir, generar_pdfs=False)

    async with abrir(tenant_b) as db:
        cobertura, contrarias = await _indicador_oe3(db)
    assert cobertura == {"CV": (1, 1)}
    assert contrarias == 0


def test_sin_contrasenas_no_carga_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    for campo in ("seed_password", "seed_password_admin"):
        monkeypatch.setattr(settings, campo, None)
    with pytest.raises(semillas.ErrorSemillas, match="SEED_PASSWORD"):
        semillas.password_de(semillas.RolUsuario.ADMIN)


def test_genera_los_20_cv_con_sus_casos_de_error(tmp_path: Path) -> None:
    """18 PDF con texto, uno escaneado sin texto y uno dañado (doc 13)."""
    rutas = generar_cvs.generar(tmp_path)

    assert len(rutas) == 20
    textos = {ruta.stem: extraer_texto_pdf(ruta.read_bytes()) for ruta in rutas}
    assert "Andrés Salazar Huamán" in textos["CV-TI-01"] and "FastAPI" in textos["CV-TI-01"]
    assert "linkedin.com/in/renzo-aguilar-ejemplo" in textos["CV-VEN-08"]
    assert textos[generar_cvs.CV_ESCANEADO].strip() == ""
    assert textos[generar_cvs.CV_DANADO].strip() == ""
    assert all(textos[codigo].strip() for codigo in textos if codigo not in (generar_cvs.CV_ESCANEADO, generar_cvs.CV_DANADO))
