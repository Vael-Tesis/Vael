"""Pruebas de la sesión de RRHH (DEC-011, DEV-A-02): login, rotación del refresh token,
detección de reutilización, logout efectivo, token_version y algoritmos aceptados."""
import base64
import json
from datetime import datetime, timezone
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import Settings, settings
from app.core.security import hash_password
from app.models.usuario import RolUsuario, Sesion, Usuario
from tests.conftest import TENANT_ID

PASSWORD = "Clave-Segura-2026"


async def _usuario(db: AsyncSession, email: str, rol: RolUsuario = RolUsuario.RECLUTADOR, activo: bool = True) -> Usuario:
    usuario = Usuario(
        tenant_id=TENANT_ID, nombre="Rocío", apellidos="Huertas", email=email,
        password_hash=await hash_password(PASSWORD), rol=rol, activo=activo,
    )
    db.add(usuario)
    await db.commit()
    return usuario


def _login(client: TestClient, email: str, password: str = PASSWORD) -> Any:
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _refresh(client: TestClient, refresh_token: str) -> Any:
    return client.post("/api/auth/refresh", json={"refresh_token": refresh_token})


def _auth(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _sesiones(db: AsyncSession, usuario_id: str) -> list[Sesion]:
    statement = select(Sesion).where(Sesion.usuario_id == usuario_id).execution_options(populate_existing=True)
    return list((await db.exec(statement.order_by(Sesion.creado_en))).all())


# --- Login (HU-01) -----------------------------------------------------------------------


async def test_login_valido_crea_la_sesion_y_un_access_de_15_minutos(client: TestClient, db_session: AsyncSession) -> None:
    usuario = await _usuario(db_session, "rocio@test.vael")

    respuesta = _login(client, "rocio@test.vael")

    assert respuesta.status_code == 200, respuesta.text
    tokens = respuesta.json()
    claims = jwt.decode(tokens["access_token"], settings.secret_key, algorithms=["HS256"])
    assert claims["type"] == "access" and claims["ver"] == 0 and claims["rol"] == "reclutador"
    duracion = datetime.fromtimestamp(claims["exp"], timezone.utc) - datetime.now(timezone.utc)
    minutos = settings.access_token_expire_minutes
    assert (minutos - 1) * 60 < duracion.total_seconds() <= minutos * 60
    assert Settings.model_fields["access_token_expire_minutes"].default == 15  # DEC-011; el CI usa 15
    assert len(await _sesiones(db_session, usuario.id)) == 1


async def test_credenciales_invalidas_401_y_usuario_inactivo_403(client: TestClient, db_session: AsyncSession) -> None:
    await _usuario(db_session, "inactivo@test.vael", activo=False)

    assert _login(client, "nadie@test.vael").status_code == 401
    assert _login(client, "inactivo@test.vael", "otra-clave").status_code == 401  # sin revelar que existe
    assert _login(client, "inactivo@test.vael").status_code == 403


async def test_la_tabla_sesiones_nunca_guarda_el_token_en_claro(
    client: TestClient, db_session: AsyncSession, system_engine: AsyncEngine
) -> None:
    await _usuario(db_session, "rocio@test.vael")
    refresh_token = _login(client, "rocio@test.vael").json()["refresh_token"]

    async with system_engine.connect() as conexion:
        filas = (await conexion.execute(text("SELECT * FROM sesiones"))).mappings().all()
    assert len(filas) == 1
    assert all(refresh_token not in str(valor) for valor in filas[0].values())
    assert len(filas[0]["token_hash"]) == 64


# --- Rotación, reutilización y logout (HU-02) -------------------------------------------


async def test_refresh_rota_el_token_y_revoca_el_anterior(client: TestClient, db_session: AsyncSession) -> None:
    usuario = await _usuario(db_session, "rocio@test.vael")
    primero = _login(client, "rocio@test.vael").json()

    renovado = _refresh(client, primero["refresh_token"])

    assert renovado.status_code == 200, renovado.text
    nuevo = renovado.json()
    assert nuevo["refresh_token"] != primero["refresh_token"]
    assert client.get("/api/auth/perfil", headers=_auth(nuevo["access_token"])).status_code == 200
    vieja, actual = await _sesiones(db_session, usuario.id)
    assert vieja.revocado_en is not None and vieja.reemplazado_por == actual.id
    assert actual.revocado_en is None


async def test_reutilizar_un_refresh_revoca_todas_las_sesiones(client: TestClient, db_session: AsyncSession) -> None:
    usuario = await _usuario(db_session, "rocio@test.vael")
    robado = _login(client, "rocio@test.vael").json()["refresh_token"]
    otra_pestana = _login(client, "rocio@test.vael").json()["refresh_token"]
    legitimo = _refresh(client, robado).json()["refresh_token"]

    reutilizado = _refresh(client, robado)

    assert reutilizado.status_code == 401
    assert _refresh(client, legitimo).status_code == 401
    assert _refresh(client, otra_pestana).status_code == 401
    assert all(s.revocado_en is not None for s in await _sesiones(db_session, usuario.id))


async def test_tras_el_logout_el_refresh_de_esa_sesion_es_rechazado(client: TestClient, db_session: AsyncSession) -> None:
    await _usuario(db_session, "rocio@test.vael")
    tokens = _login(client, "rocio@test.vael").json()

    cerrar = client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=_auth(tokens["access_token"]))

    assert cerrar.status_code == 200
    assert _refresh(client, tokens["refresh_token"]).status_code == 401


async def test_no_se_cierra_la_sesion_de_otro_usuario(client: TestClient, db_session: AsyncSession) -> None:
    await _usuario(db_session, "a@test.vael")
    await _usuario(db_session, "b@test.vael")
    a = _login(client, "a@test.vael").json()
    b = _login(client, "b@test.vael").json()

    respuesta = client.post("/api/auth/logout", json={"refresh_token": b["refresh_token"]}, headers=_auth(a["access_token"]))

    assert respuesta.status_code == 401
    assert _refresh(client, b["refresh_token"]).status_code == 200


# --- token_version (HU-02, HU-07) --------------------------------------------------------


@pytest.mark.parametrize(
    ("ruta", "cuerpo"),
    [("desactivar", None), ("cambiar-password", {"password_nueva": "Nueva-Clave-2026"})],
)
async def test_desactivar_o_cambiar_la_contrasena_invalida_los_tokens_al_instante(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, ruta: str, cuerpo: dict[str, str] | None
) -> None:
    usuario = await _usuario(db_session, "rocio@test.vael")
    tokens = _login(client, "rocio@test.vael").json()
    assert client.get("/api/auth/perfil", headers=_auth(tokens["access_token"])).status_code == 200

    respuesta = client.put(f"/api/auth/usuarios/{usuario.id}/{ruta}", json=cuerpo, headers=admin_headers)

    assert respuesta.status_code == 200, respuesta.text
    assert client.get("/api/auth/perfil", headers=_auth(tokens["access_token"])).status_code == 401
    assert _refresh(client, tokens["refresh_token"]).status_code == 401


# --- Algoritmos ---------------------------------------------------------------------------


def _b64(datos: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()


async def test_token_con_alg_none_u_otro_algoritmo_es_rechazado(client: TestClient, db_session: AsyncSession) -> None:
    usuario = await _usuario(db_session, "rocio@test.vael")
    claims = {"sub": usuario.id, "tenant_id": TENANT_ID, "rol": "admin", "type": "access", "ver": 0, "exp": 4102444800}

    sin_firma = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(claims)}."
    otro_algoritmo = jwt.encode(claims, settings.secret_key, algorithm="HS512")
    otra_clave = jwt.encode(claims, "otra-clave-de-al-menos-32-caracteres!!", algorithm="HS256")
    sin_exp = jwt.encode({k: v for k, v in claims.items() if k != "exp"}, settings.secret_key, algorithm="HS256")

    for token in (sin_firma, otro_algoritmo, otra_clave, sin_exp):
        assert client.get("/api/auth/perfil", headers=_auth(token)).status_code == 401
