"""CA-03 (HU-03): el backend rechaza con 403 lo que un rol no puede hacer, aunque se intente
fuera de la interfaz. El evaluador solo consulta: ninguna ruta de escritura lo acepta.

La lista de rutas sale de la propia app, así una ruta nueva queda cubierta sin tocar el test.
"""
import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models.usuario import RolUsuario, Usuario
from tests.conftest import TENANT_ID

# Rutas de escritura que no son de RRHH (público, candidato, sesión) o que el evaluador sí puede usar
_EXCLUIDAS = [
    r"^/api/publico/",
    r"^/api/evaluaciones/candidato/",
    r"^/api/entrevista/(acceso|iniciar|finalizar|captura|evento)$",
    r"^/api/auth/(login|refresh|logout)$",
    r"^/api/candidatos/\{candidato_id\}/notas",  # notas: cualquier rol autenticado (doc 06)
]


def _rutas_de_escritura() -> list[tuple[str, str]]:
    rutas = []
    for ruta in app.routes:
        if not isinstance(ruta, APIRoute) or not ruta.path.startswith("/api/"):
            continue
        if any(re.search(patron, ruta.path) for patron in _EXCLUIDAS):
            continue
        for metodo in sorted(ruta.methods - {"GET", "HEAD", "OPTIONS"}):
            rutas.append((metodo, ruta.path))
    return rutas


RUTAS = _rutas_de_escritura()


def test_hay_rutas_de_escritura_que_cubrir() -> None:
    assert len(RUTAS) > 30


@pytest.fixture
async def evaluador_headers(db_session: AsyncSession) -> dict[str, str]:
    usuario = Usuario(
        tenant_id=TENANT_ID, nombre="Ernesto", apellidos="Valdivia", email="evaluador@test.vael",
        password_hash="x", rol=RolUsuario.EVALUADOR,
    )
    db_session.add(usuario)
    await db_session.commit()
    return {"Authorization": f"Bearer {await create_access_token(usuario.id, TENANT_ID, usuario.rol.value)}"}


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS, ids=[f"{m} {r}" for m, r in RUTAS])
def test_el_evaluador_no_escribe(client: TestClient, evaluador_headers: dict[str, str], metodo: str, ruta: str) -> None:
    url = re.sub(r"\{[^}]+\}", "x", ruta)
    respuesta = client.request(metodo, url, json={}, headers=evaluador_headers)
    assert respuesta.status_code == 403, f"{metodo} {ruta} respondió {respuesta.status_code}"
