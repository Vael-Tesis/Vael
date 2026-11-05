"""Matriz de permisos por rol — TST-A-02 (HU-25), contra los niveles del doc 06 y el doc 15.

Un usuario de cada rol (admin, gerente, reclutador, evaluador) del mismo tenant intenta cada
uno de los endpoints autenticados de RRHH: la prueba falla si un rol accede a algo que no le
corresponde (no responde 403) o si se le niega algo que sí le corresponde (responde 403).

Cobertura automática: la lista de endpoints sale de `_rutas_autenticadas_rrhh()`
(`tests/test_aislamiento_multiempresa.py`, TST-C-01) — la misma introspección del árbol de
dependencias de FastAPI — así ningún endpoint nuevo queda fuera de la matriz
(`test_la_matriz_cubre_todos_los_endpoints_rrhh`).

Dos endpoints (`PUT`/`DELETE /candidatos/{id}/notas/{nota_id}`) no tienen un nivel por rol:
los permite cualquier rol autenticado, pero la autoría de la nota decide (doc 06, "Autor de
la nota" / "Autor o admin"); quedan fuera de la matriz por rol, con su propia justificación,
y ya los cubre `test_notas_etiquetas_areas.py::test_solo_el_autor_edita_y_el_autor_o_un_admin_eliminan`
(RF-A-13).
"""
from dataclasses import asdict, dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.area import Area
from app.models.candidato import Candidato, EstadoCandidato, NotaCandidato, Tag
from app.models.entrevista import DimensionEvaluacion, EntrevistaIA, PlantillaEvaluacion
from app.models.evaluacion import Examen
from app.models.usuario import Empresa, RolUsuario, Usuario
from app.models.vacante import EstadoVacante, Vacante
from tests.conftest import TENANT_ID
from tests.test_aislamiento_multiempresa import _rutas_autenticadas_rrhh

PASSWORD = "Clave-Matriz-2026"

ADMIN, GERENTE, RECLUTADOR, EVALUADOR = RolUsuario.ADMIN, RolUsuario.GERENTE, RolUsuario.RECLUTADOR, RolUsuario.EVALUADOR
ROLES = (ADMIN, GERENTE, RECLUTADOR, EVALUADOR)

# Los cuatro niveles de permiso de RRHH del doc 06 (Público, Candidato e Interno no aplican
# a esta matriz: ya quedan fuera de _rutas_autenticadas_rrhh).
AUTENTICADO = frozenset(ROLES)
RECLUTADOR_O_SUPERIOR = frozenset({ADMIN, GERENTE, RECLUTADOR})
ADMIN_O_GERENTE = frozenset({ADMIN, GERENTE})
SOLO_ADMIN = frozenset({ADMIN})


# --- Recursos de un solo tenant, para construir rutas y cuerpos válidos -----------------


@dataclass(frozen=True)
class Recursos:
    """Un recurso de cada tipo en TENANT_ID, para resolver los `{campo}` de la tabla."""

    area_id: str
    vacante_id: str
    candidato_id: str
    nota_id: str
    tag_id: str
    plantilla_id: str
    dimension_id: str
    usuario_id: str
    examen_id: str
    entrevista_id: str


@pytest.fixture
async def recursos(db_session: AsyncSession) -> Recursos:
    """Crea un recurso de cada tipo en el tenant de prueba (mismo tenant que los 4 roles)."""
    empresa = Empresa(tenant_id=TENANT_ID, nombre="Andina Servicios S.A.C.", email_contacto="rrhh@andina.example.com")
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    db_session.add_all([empresa, area])
    await db_session.flush()

    vacante = Vacante(
        tenant_id=TENANT_ID, area_id=area.id, codigo="TI-2026-800", titulo="Vacante de prueba", estado=EstadoVacante.ABIERTA
    )
    plantilla = PlantillaEvaluacion(tenant_id=TENANT_ID, nombre="Plantilla de prueba")
    tag = Tag(tenant_id=TENANT_ID, nombre="Backend-matriz")
    # Usuario a modificar por los endpoints de gestión de usuarios (nunca el actor bajo prueba).
    usuario_objetivo = Usuario(
        tenant_id=TENANT_ID, nombre="Rocío", apellidos="Huertas", email="objetivo@matriz.test.vael",
        password_hash="no-usado", rol=RolUsuario.RECLUTADOR,
    )
    autor_nota = Usuario(
        tenant_id=TENANT_ID, nombre="Lucía", apellidos="Quispe", email="autora-nota@matriz.test.vael",
        password_hash="no-usado", rol=RolUsuario.RECLUTADOR,
    )
    db_session.add_all([vacante, plantilla, tag, usuario_objetivo, autor_nota])
    await db_session.flush()

    dimension = DimensionEvaluacion(tenant_id=TENANT_ID, plantilla_id=plantilla.id, nombre="Comunicación", peso=100.0)
    candidato = Candidato(
        tenant_id=TENANT_ID, vacante_id=vacante.id, nombre="Mario", apellidos="Rojas", email="mario.matriz@example.com",
        estado=EstadoCandidato.CV_POR_CONFIRMAR,
    )
    db_session.add_all([dimension, candidato])
    await db_session.flush()

    nota = NotaCandidato(tenant_id=TENANT_ID, candidato_id=candidato.id, autor_id=autor_nota.id, contenido="Nota de prueba")
    examen = Examen(tenant_id=TENANT_ID, candidato_id=candidato.id, vacante_id=vacante.id)
    entrevista = EntrevistaIA(tenant_id=TENANT_ID, candidato_id=candidato.id, vacante_id=vacante.id)
    db_session.add_all([nota, examen, entrevista])
    await db_session.commit()

    return Recursos(
        area_id=area.id, vacante_id=vacante.id, candidato_id=candidato.id, nota_id=nota.id, tag_id=tag.id,
        plantilla_id=plantilla.id, dimension_id=dimension.id, usuario_id=usuario_objetivo.id, examen_id=examen.id,
        entrevista_id=entrevista.id,
    )


@pytest.fixture
async def headers_por_rol(db_session: AsyncSession) -> dict[RolUsuario, dict[str, str]]:
    """Headers Authorization de un usuario de cada rol, todos en TENANT_ID."""
    usuarios = {
        rol: Usuario(
            tenant_id=TENANT_ID, nombre="Test", apellidos=rol.value, email=f"{rol.value}@matriz.test.vael",
            password_hash="no-usado-en-estos-tests", rol=rol,
        )
        for rol in ROLES
    }
    db_session.add_all(usuarios.values())
    await db_session.commit()
    for usuario in usuarios.values():
        await db_session.refresh(usuario)

    return {
        rol: {"Authorization": f"Bearer {await create_access_token(usuario.id, usuario.tenant_id, usuario.rol.value)}"}
        for rol, usuario in usuarios.items()
    }


# --- Tabla de endpoints RRHH: nivel y cuerpo válido (si aplica) ------------------------


@dataclass(frozen=True)
class CasoPermiso:
    metodo: str
    ruta: str  # con placeholders {campo}, resueltos contra `Recursos`
    permite: frozenset[RolUsuario]
    cuerpo: dict[str, Any] | None = None
    query: dict[str, Any] | None = None


CASOS: list[CasoPermiso] = [
    # --- auth ---
    CasoPermiso("GET", "/api/auth/perfil", AUTENTICADO),
    CasoPermiso("POST", "/api/auth/usuarios/crear", SOLO_ADMIN, cuerpo={
        "nombre": "Nueva", "apellidos": "Persona", "email": "nueva.persona@matriz.test.vael", "rol": "reclutador",
    }),
    CasoPermiso("GET", "/api/auth/usuarios", ADMIN_O_GERENTE),
    CasoPermiso("PUT", "/api/auth/usuarios/{usuario_id}/activar", SOLO_ADMIN),
    CasoPermiso("PUT", "/api/auth/usuarios/{usuario_id}/desactivar", SOLO_ADMIN),
    CasoPermiso("PUT", "/api/auth/usuarios/{usuario_id}/cambiar-password", SOLO_ADMIN, cuerpo={"password_nueva": "Nueva-Clave-12345678"}),
    CasoPermiso("POST", "/api/auth/usuarios/{usuario_id}/reenviar-credenciales", SOLO_ADMIN),
    # --- áreas ---
    CasoPermiso("GET", "/api/areas", AUTENTICADO),
    CasoPermiso("POST", "/api/areas", ADMIN_O_GERENTE, cuerpo={"nombre": "Nueva área", "codigo_corto": "NV"}),
    CasoPermiso("GET", "/api/areas/{area_id}", AUTENTICADO),
    CasoPermiso("PUT", "/api/areas/{area_id}", ADMIN_O_GERENTE, cuerpo={"nombre": "Área editada"}),
    CasoPermiso("POST", "/api/areas/{area_id}/activar", ADMIN_O_GERENTE),
    CasoPermiso("POST", "/api/areas/{area_id}/desactivar", ADMIN_O_GERENTE),
    CasoPermiso("DELETE", "/api/areas/{area_id}", SOLO_ADMIN),
    # --- plantillas ---
    CasoPermiso("GET", "/api/plantillas", AUTENTICADO),
    CasoPermiso("POST", "/api/plantillas", ADMIN_O_GERENTE, cuerpo={
        "nombre": "Plantilla nueva", "dimensiones": [{"nombre": "Única", "peso": 100.0}],
    }),
    CasoPermiso("GET", "/api/plantillas/{plantilla_id}", AUTENTICADO),
    CasoPermiso("PUT", "/api/plantillas/{plantilla_id}", ADMIN_O_GERENTE, cuerpo={"nombre": "Plantilla editada"}),
    CasoPermiso("POST", "/api/plantillas/{plantilla_id}/dimensiones", ADMIN_O_GERENTE, cuerpo={"nombre": "Nueva", "peso": 50.0}),
    CasoPermiso("PUT", "/api/plantillas/{plantilla_id}/dimensiones/{dimension_id}", ADMIN_O_GERENTE, cuerpo={"nombre": "x"}),
    CasoPermiso("DELETE", "/api/plantillas/{plantilla_id}/dimensiones/{dimension_id}", ADMIN_O_GERENTE),
    # --- vacantes ---
    CasoPermiso("GET", "/api/vacantes", AUTENTICADO),
    CasoPermiso("POST", "/api/vacantes", RECLUTADOR_O_SUPERIOR, cuerpo={"area_id": "{area_id}", "titulo": "Vacante nueva"}),
    CasoPermiso("GET", "/api/vacantes/{vacante_id}", AUTENTICADO),
    CasoPermiso("PUT", "/api/vacantes/{vacante_id}", RECLUTADOR_O_SUPERIOR, cuerpo={"titulo": "Vacante editada"}),
    CasoPermiso("DELETE", "/api/vacantes/{vacante_id}", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/vacantes/{vacante_id}/publicar", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/vacantes/{vacante_id}/pausar", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/vacantes/{vacante_id}/cerrar", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/vacantes/{vacante_id}/duplicar", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/vacantes/{vacante_id}/generar-textos", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("GET", "/api/vacantes/{vacante_id}/textos", AUTENTICADO),
    CasoPermiso("PUT", "/api/vacantes/{vacante_id}/textos", RECLUTADOR_O_SUPERIOR, cuerpo={"textos": {"linkedin": "x"}}),
    # --- candidatos ---
    CasoPermiso("GET", "/api/candidatos", AUTENTICADO),
    CasoPermiso("GET", "/api/candidatos/{candidato_id}", AUTENTICADO),
    CasoPermiso("PUT", "/api/candidatos/{candidato_id}", RECLUTADOR_O_SUPERIOR, cuerpo={"nombre": "Candidato editado"}),
    CasoPermiso("POST", "/api/candidatos/{candidato_id}/analizar", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/candidatos/{candidato_id}/cambiar-estado", RECLUTADOR_O_SUPERIOR, cuerpo={"estado": "postulado"}),
    CasoPermiso("POST", "/api/candidatos/{candidato_id}/reenviar-correo-etapa", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("GET", "/api/candidatos/{candidato_id}/notas", AUTENTICADO),
    CasoPermiso("POST", "/api/candidatos/{candidato_id}/notas", AUTENTICADO, cuerpo={"contenido": "Nota desde la matriz"}),
    CasoPermiso("POST", "/api/candidatos/{candidato_id}/tags", RECLUTADOR_O_SUPERIOR, cuerpo={"tag_id": "{tag_id}"}),
    CasoPermiso("DELETE", "/api/candidatos/{candidato_id}/tags/{tag_id}", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/candidatos/{candidato_id}/banco-talento", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("GET", "/api/candidatos/ranking", AUTENTICADO, query={"vacante_id": "{vacante_id}"}),
    CasoPermiso("GET", "/api/candidatos/banco-talento", AUTENTICADO),
    CasoPermiso("GET", "/api/candidatos/por-confirmar", RECLUTADOR_O_SUPERIOR),
    CasoPermiso("POST", "/api/candidatos/{candidato_id}/decision", RECLUTADOR_O_SUPERIOR, cuerpo={"etapa": "cv", "decision": "avanzar"}),
    CasoPermiso(
        "POST", "/api/candidatos/decisiones/lote", RECLUTADOR_O_SUPERIOR,
        cuerpo={"etapa": "cv", "decisiones": [{"candidato_id": "{candidato_id}", "decision": "avanzar"}]},
    ),
    CasoPermiso("GET", "/api/candidatos/{candidato_id}/decisiones", AUTENTICADO),
    # --- tags ---
    CasoPermiso("GET", "/api/tags", AUTENTICADO),
    CasoPermiso("POST", "/api/tags", RECLUTADOR_O_SUPERIOR, cuerpo={"nombre": "Etiqueta nueva"}),
    CasoPermiso("PUT", "/api/tags/{tag_id}", RECLUTADOR_O_SUPERIOR, cuerpo={"nombre": "Etiqueta editada"}),
    CasoPermiso("DELETE", "/api/tags/{tag_id}", ADMIN_O_GERENTE),
    # --- métricas ---
    CasoPermiso("GET", "/api/metricas/dashboard", AUTENTICADO),
    # --- entrevista / evaluaciones (solo lectura RRHH) ---
    CasoPermiso("GET", "/api/entrevista", AUTENTICADO),
    CasoPermiso("GET", "/api/entrevista/detalle/{entrevista_id}", AUTENTICADO),
    CasoPermiso("GET", "/api/evaluaciones/examenes", AUTENTICADO),
    CasoPermiso("GET", "/api/evaluaciones/examenes/{examen_id}", AUTENTICADO),
    CasoPermiso("GET", "/api/evaluaciones/examenes/{examen_id}/auditoria", AUTENTICADO),
    CasoPermiso("GET", "/api/evaluaciones/auditoria", AUTENTICADO),
]


def _resolver(valor: Any, recursos: Recursos) -> Any:
    if isinstance(valor, str):
        return valor.format(**asdict(recursos))
    if isinstance(valor, dict):
        return {k: _resolver(v, recursos) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_resolver(v, recursos) for v in valor]
    return valor


@pytest.mark.parametrize("caso", CASOS, ids=[f"{c.metodo} {c.ruta}" for c in CASOS])
@pytest.mark.parametrize("rol", ROLES, ids=[r.value for r in ROLES])
async def test_matriz_de_permisos(
    client: TestClient, headers_por_rol: dict[RolUsuario, dict[str, str]], recursos: Recursos,
    rol: RolUsuario, caso: CasoPermiso,
) -> None:
    """Cada rol recibe exactamente el acceso que el doc 06/15 le asigna para este endpoint."""
    ruta = _resolver(caso.ruta, recursos)
    cuerpo = _resolver(caso.cuerpo, recursos) if caso.cuerpo is not None else None
    query = _resolver(caso.query, recursos) if caso.query is not None else None

    respuesta = client.request(caso.metodo, ruta, json=cuerpo, params=query, headers=headers_por_rol[rol])

    if rol in caso.permite:
        assert respuesta.status_code != 403, (
            f"{rol.value} debería poder usar {caso.metodo} {ruta}, pero respondió 403: {respuesta.text}"
        )
    else:
        assert respuesta.status_code == 403, (
            f"{rol.value} no debería poder usar {caso.metodo} {ruta}, pero respondió "
            f"{respuesta.status_code} (no 403): {respuesta.text}"
        )


# --- Casos que no caben en la tabla genérica (multipart y login) ------------------------


@pytest.mark.parametrize("rol", ROLES, ids=[r.value for r in ROLES])
async def test_matriz_crear_candidato_multipart(
    client: TestClient, headers_por_rol: dict[RolUsuario, dict[str, str]], recursos: Recursos, rol: RolUsuario
) -> None:
    """POST /candidatos (multipart) es Reclutador+; el evaluador recibe 403."""
    archivo = {"cv": ("cv.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")}
    datos = {"vacante_id": recursos.vacante_id, "nombre": "X", "apellidos": "Y", "email": "candidato.matriz@example.com"}
    respuesta = client.post("/api/candidatos", data=datos, files=archivo, headers=headers_por_rol[rol])
    if rol in RECLUTADOR_O_SUPERIOR:
        assert respuesta.status_code != 403, respuesta.text
    else:
        assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize("rol", ROLES, ids=[r.value for r in ROLES])
async def test_matriz_carga_masiva_multipart(
    client: TestClient, headers_por_rol: dict[RolUsuario, dict[str, str]], recursos: Recursos, rol: RolUsuario
) -> None:
    """POST /candidatos/carga-masiva (multipart) es Reclutador+; el evaluador recibe 403."""
    archivo = {"archivos": ("cv.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")}
    respuesta = client.post(
        "/api/candidatos/carga-masiva", data={"vacante_id": recursos.vacante_id}, files=archivo, headers=headers_por_rol[rol]
    )
    if rol in RECLUTADOR_O_SUPERIOR:
        assert respuesta.status_code != 403, respuesta.text
    else:
        assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize("rol", ROLES, ids=[r.value for r in ROLES])
async def test_matriz_logout_es_autenticado(
    client: TestClient, db_session: AsyncSession, rol: RolUsuario
) -> None:
    """POST /auth/logout es Autenticado: ningún rol recibe 403 (RF-A-02)."""
    usuario = Usuario(
        tenant_id=TENANT_ID, nombre="Login", apellidos=rol.value, email=f"logout-{rol.value}@matriz.test.vael",
        password_hash=await hash_password(PASSWORD), rol=rol,
    )
    db_session.add(usuario)
    await db_session.commit()

    login = client.post("/api/auth/login", json={"email": usuario.email, "password": PASSWORD})
    assert login.status_code == 200, login.text

    respuesta = client.post(
        "/api/auth/logout", json={"refresh_token": login.json()["refresh_token"]},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert respuesta.status_code != 403, respuesta.text


async def test_usuario_inactivo_no_inicia_sesion(client: TestClient, db_session: AsyncSession) -> None:
    """RF-A-01: credenciales válidas pero usuario inactivo → 403 (no 401: la contraseña es correcta)."""
    usuario = Usuario(
        tenant_id=TENANT_ID, nombre="Inactiva", apellidos="Prueba", email="inactivo@matriz.test.vael",
        password_hash=await hash_password(PASSWORD), rol=RolUsuario.RECLUTADOR, activo=False,
    )
    db_session.add(usuario)
    await db_session.commit()

    respuesta = client.post("/api/auth/login", json={"email": usuario.email, "password": PASSWORD})
    assert respuesta.status_code == 403, respuesta.text


# --- Cobertura automática: ningún endpoint RRHH queda fuera de la matriz ---------------


# PUT/DELETE /notas/{nota_id}: cualquier rol autenticado puede intentarlo (no hay un nivel
# por rol que negar); la autoría decide. Ya cubierto por RF-A-13 en test_notas_etiquetas_areas.py.
_SIN_NIVEL_POR_ROL = {
    ("PUT", "/api/candidatos/{candidato_id}/notas/{nota_id}"),
    ("DELETE", "/api/candidatos/{candidato_id}/notas/{nota_id}"),
}

_CUBIERTAS_FUERA_DE_TABLA = {
    ("POST", "/api/candidatos"),
    ("POST", "/api/candidatos/carga-masiva"),
    ("POST", "/api/auth/logout"),
}


def test_la_matriz_cubre_todos_los_endpoints_rrhh() -> None:
    """Todo endpoint RRHH autenticado tiene un caso en esta matriz, o queda excluido con
    justificación (CA de TST-A-02: 100% de los endpoints de RRHH)."""
    vivas = _rutas_autenticadas_rrhh()
    de_tabla = {(c.metodo, c.ruta) for c in CASOS}
    cubiertas = de_tabla | _CUBIERTAS_FUERA_DE_TABLA | _SIN_NIVEL_POR_ROL

    faltantes = vivas - cubiertas
    assert faltantes == set(), f"Endpoints RRHH sin caso en la matriz de permisos: {sorted(faltantes)}"

    de_mas = cubiertas - vivas
    assert de_mas == set(), f"Casos de la matriz que ya no corresponden a un endpoint RRHH vivo: {sorted(de_mas)}"
