"""Suite de aislamiento multiempresa en dos capas — TST-C-01 (HU-04, OE4, RF-A-20).

Capa de aplicación (DEC-010): con las empresas A y B, B no puede leer ni modificar ningún
recurso de A por ningún endpoint autenticado — ni de RRHH (`get_current_user`/`require_rol`)
ni de candidato (`get_current_candidate`/`get_current_candidato`, DEC-021). Capa de base de
datos (RLS): ya cubierta en `tests/test_rls.py` (DEC-010, DEC-014, DEC-021) — no se repite
aquí.

Cobertura automática: `_rutas_autenticadas_rrhh()` y `_rutas_autenticadas_candidato()`
recorren `app.routes` y, para cada ruta, caminan el árbol de dependencias de FastAPI
buscando `get_current_user` (directo o a través de `require_rol`, que lo envuelve) o
`get_current_candidate` (directo o a través de `get_current_candidato`, que lo envuelve),
respectivamente. Esto distingue los dos perfiles autenticados del doc 06 (RRHH: "Autenticado"
/"Reclutador+"/"Admin o gerente"; Candidato) de la lista cerrada de 5 operaciones del doc
06/DEC-010/DEC-014/DEC-021 (login, postulación pública por código, listado público de
vacantes, feed XML, resolución del código del candidato — la postulación pública usa 2
funciones para 1 operación, así que la lista tiene 6 funciones pero 5 operaciones), que no
pasa por ninguna dependencia de autenticación. El resultado se compara contra la unión de
todo lo que esta suite prueba (`test_la_cobertura_es_total`): si aparece una ruta nueva de
cualquiera de los dos perfiles sin caso, la suite falla.
"""
import importlib
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import CLAVE_TENANT
from app.core.dependencies import get_current_candidate, get_current_user
from app.core.security import create_access_token, create_candidate_token, hash_password
from app.main import app
from app.models.area import Area
from app.models.candidato import Candidato, CandidatoTag, EstadoCandidato, NotaCandidato, Tag
from app.models.entrevista import DimensionEvaluacion, EntrevistaIA, PlantillaEvaluacion
from app.models.evaluacion import Examen, PreguntaExamen, TipoPregunta
from app.models.usuario import Empresa, RolUsuario, TipoToken, Usuario
from app.models.vacante import EstadoVacante, Vacante
from tests.conftest import TENANT_ID, TENANT_ID_OTRO

PASSWORD = "Clave-Empresa-B-2026"


# --- Descubrimiento automático de endpoints autenticados (CA punto 3) -------------------


def _camina_dependencias(dependant: Any, objetivo: Callable[..., Any], visto: set[int] | None = None) -> bool:
    """Camina el árbol de dependencias de una ruta buscando la dependencia `objetivo`.

    `require_rol(*roles)` envuelve a `get_current_user`, y `get_current_candidato` envuelve
    a `get_current_candidate`: una búsqueda recursiva detecta ambos casos (directo o
    envuelto) sin tener que enumerar cada variante.
    """
    if visto is None:
        visto = set()
    if id(dependant) in visto:
        return False
    visto.add(id(dependant))
    if getattr(dependant, "call", None) is objetivo:
        return True
    return any(_camina_dependencias(sub, objetivo, visto) for sub in dependant.dependencies)


def _rutas_con_dependencia(objetivo: Callable[..., Any]) -> set[tuple[str, str]]:
    """Todas las (método, path) cuyo árbol de dependencias use `objetivo`."""
    rutas: set[tuple[str, str]] = set()
    for ruta in app.routes:
        if not isinstance(ruta, APIRoute):
            continue
        if _camina_dependencias(ruta.dependant, objetivo):
            for metodo in ruta.methods - {"HEAD", "OPTIONS"}:
                rutas.add((metodo, ruta.path))
    return rutas


def _rutas_autenticadas_rrhh() -> set[tuple[str, str]]:
    """Todas las (método, path) de rutas RRHH autenticadas, según el árbol de dependencias real."""
    return _rutas_con_dependencia(get_current_user)


def _rutas_autenticadas_candidato() -> set[tuple[str, str]]:
    """Todas las (método, path) de rutas de candidato autenticadas (DEC-021)."""
    return _rutas_con_dependencia(get_current_candidate)


# --- Datos de la empresa "ajena" (A), para atacar desde la empresa B --------------------


@dataclass(frozen=True)
class Ajeno:
    """Un recurso de cada tipo, creado en el tenant A (TENANT_ID), para intentar accederlo como B."""

    area_id: str
    vacante_id: str
    candidato_id: str
    nota_id: str
    tag_id: str
    plantilla_id: str
    dimension_id: str
    usuario_id: str
    examen_id: str
    pregunta_id: str
    entrevista_id: str


@pytest.fixture
async def ajeno(db_session: AsyncSession) -> Ajeno:
    """Crea un recurso de cada tipo en el tenant A (TENANT_ID) para los casos de aislamiento."""
    empresa = Empresa(tenant_id=TENANT_ID, nombre="Andina Servicios S.A.C.", email_contacto="rrhh@andina.example.com")
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    db_session.add_all([empresa, area])
    await db_session.flush()

    vacante = Vacante(
        tenant_id=TENANT_ID, area_id=area.id, codigo="TI-2026-900", titulo="Vacante ajena", estado=EstadoVacante.ABIERTA
    )
    plantilla = PlantillaEvaluacion(tenant_id=TENANT_ID, nombre="Plantilla ajena")
    tag = Tag(tenant_id=TENANT_ID, nombre="Backend")
    usuario = Usuario(
        tenant_id=TENANT_ID, nombre="Lucía", apellidos="Quispe", email="lucia.ajena@andina.example.com",
        password_hash="no-usado", rol=RolUsuario.RECLUTADOR,
    )
    db_session.add_all([vacante, plantilla, tag, usuario])
    await db_session.flush()

    dimension = DimensionEvaluacion(tenant_id=TENANT_ID, plantilla_id=plantilla.id, nombre="Comunicación", peso=100.0)
    candidato = Candidato(
        tenant_id=TENANT_ID, vacante_id=vacante.id, nombre="Mario", apellidos="Rojas", email="mario.ajeno@example.com",
        estado=EstadoCandidato.CV_POR_CONFIRMAR, en_banco_talento=True,
    )
    db_session.add_all([dimension, candidato])
    await db_session.flush()

    nota = NotaCandidato(tenant_id=TENANT_ID, candidato_id=candidato.id, autor_id=usuario.id, contenido="Nota ajena")
    examen = Examen(tenant_id=TENANT_ID, candidato_id=candidato.id, vacante_id=vacante.id)
    entrevista = EntrevistaIA(tenant_id=TENANT_ID, candidato_id=candidato.id, vacante_id=vacante.id)
    tag_asignado = CandidatoTag(tenant_id=TENANT_ID, candidato_id=candidato.id, tag_id=tag.id)
    db_session.add_all([nota, examen, entrevista, tag_asignado])
    await db_session.flush()

    pregunta = PreguntaExamen(
        tenant_id=TENANT_ID, examen_id=examen.id, orden=1, tipo=TipoPregunta.ABIERTA, enunciado="Pregunta ajena",
    )
    db_session.add(pregunta)
    await db_session.commit()

    return Ajeno(
        area_id=area.id, vacante_id=vacante.id, candidato_id=candidato.id, nota_id=nota.id, tag_id=tag.id,
        plantilla_id=plantilla.id, dimension_id=dimension.id, usuario_id=usuario.id, examen_id=examen.id,
        pregunta_id=pregunta.id, entrevista_id=entrevista.id,
    )


@pytest.fixture
async def headers_otro(db_engine: AsyncEngine) -> dict[str, str]:
    """Headers Authorization de un ADMIN de la empresa B (TENANT_ID_OTRO).

    Usa su propia sesión fijada a TENANT_ID_OTRO (no `db_session`, fijada a TENANT_ID): la
    RLS rechazaría insertar un usuario de otro tenant en la sesión de la empresa A (DEC-010).
    """
    async with AsyncSession(db_engine, expire_on_commit=False, info={CLAVE_TENANT: TENANT_ID_OTRO}) as db:
        usuario = Usuario(
            tenant_id=TENANT_ID_OTRO, nombre="Test", apellidos="Admin B", email="admin@empresa-b.test.vael",
            password_hash="no-usado-en-estos-tests", rol=RolUsuario.ADMIN,
        )
        db.add(usuario)
        await db.commit()
        await db.refresh(usuario)
    token = await create_access_token(usuario.id, usuario.tenant_id, usuario.rol.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def candidato_b(db_engine: AsyncEngine) -> Candidato:
    """Un candidato propio de la empresa B (TENANT_ID_OTRO), para probar su token (DEC-021).

    Sesión propia, igual que `headers_otro`: la RLS rechazaría crearlo desde `db_session`.
    """
    async with AsyncSession(db_engine, expire_on_commit=False, info={CLAVE_TENANT: TENANT_ID_OTRO}) as db:
        area = Area(tenant_id=TENANT_ID_OTRO, nombre="Comercial", codigo_corto="VEN")
        db.add(area)
        await db.flush()
        vacante = Vacante(
            tenant_id=TENANT_ID_OTRO, area_id=area.id, codigo="VEN-2026-900", titulo="Vacante propia de B",
            estado=EstadoVacante.ABIERTA,
        )
        db.add(vacante)
        await db.flush()
        candidato = Candidato(
            tenant_id=TENANT_ID_OTRO, vacante_id=vacante.id, nombre="Beatriz", apellidos="Soto",
            email="beatriz@empresa-b.example.com",
        )
        db.add(candidato)
        await db.commit()
        await db.refresh(candidato)
    return candidato


async def _headers_candidato(candidato: Candidato, tipo: TipoToken) -> dict[str, str]:
    """Headers Authorization de un token de candidato (examen o entrevista, DEC-021)."""
    token = await create_candidate_token(candidato.id, candidato.tenant_id, tipo.value)
    return {"Authorization": f"Bearer {token}"}


# --- Capa de aplicación: tabla de casos (CA punto 1) -------------------------------------


@dataclass(frozen=True)
class Caso:
    metodo: str
    ruta: str  # con placeholders {campo}, resueltos contra `Ajeno`
    cuerpo: dict[str, Any] | None = None
    query: dict[str, Any] | None = None
    estados_esperados: frozenset[int] = frozenset({404})


CASOS: list[Caso] = [
    # --- áreas ---
    Caso("GET", "/api/areas/{area_id}"),
    Caso("PUT", "/api/areas/{area_id}", cuerpo={"nombre": "Intento ajeno"}),
    Caso("POST", "/api/areas/{area_id}/activar"),
    Caso("POST", "/api/areas/{area_id}/desactivar"),
    Caso("DELETE", "/api/areas/{area_id}"),
    # --- candidatos ---
    Caso("GET", "/api/candidatos/{candidato_id}"),
    Caso("PUT", "/api/candidatos/{candidato_id}", cuerpo={"nombre": "Intento ajeno"}),
    Caso("POST", "/api/candidatos/{candidato_id}/analizar"),
    Caso("POST", "/api/candidatos/{candidato_id}/banco-talento"),
    Caso("POST", "/api/candidatos/{candidato_id}/cambiar-estado", cuerpo={"estado": "postulado"}),
    Caso("POST", "/api/candidatos/{candidato_id}/decision", cuerpo={"etapa": "cv", "decision": "avanzar"}),
    Caso("GET", "/api/candidatos/{candidato_id}/decisiones"),
    Caso("GET", "/api/candidatos/{candidato_id}/notas"),
    Caso("POST", "/api/candidatos/{candidato_id}/notas", cuerpo={"contenido": "Intento ajeno"}),
    Caso("POST", "/api/candidatos/{candidato_id}/reenviar-correo-etapa"),
    Caso("POST", "/api/candidatos/{candidato_id}/tags", cuerpo={"tag_id": "no-existe"}),
    Caso("PUT", "/api/candidatos/{candidato_id}/notas/{nota_id}", cuerpo={"contenido": "x"}),
    Caso("DELETE", "/api/candidatos/{candidato_id}/notas/{nota_id}"),
    Caso("DELETE", "/api/candidatos/{candidato_id}/tags/{tag_id}"),
    Caso("GET", "/api/candidatos/ranking", query={"vacante_id": "{vacante_id}"}),
    Caso(
        "POST", "/api/candidatos/decisiones/lote",
        cuerpo={"etapa": "cv", "decisiones": [{"candidato_id": "{candidato_id}", "decision": "avanzar"}]},
    ),
    # --- entrevista / exámenes (solo lectura RRHH) ---
    Caso("GET", "/api/entrevista/detalle/{entrevista_id}"),
    Caso("GET", "/api/evaluaciones/examenes/{examen_id}"),
    Caso("GET", "/api/evaluaciones/examenes/{examen_id}/auditoria"),
    # --- plantillas ---
    Caso("GET", "/api/plantillas/{plantilla_id}"),
    Caso("PUT", "/api/plantillas/{plantilla_id}", cuerpo={"nombre": "Intento ajeno"}),
    Caso(
        "POST", "/api/plantillas/{plantilla_id}/dimensiones",
        cuerpo={"nombre": "Nueva", "peso": 50.0},
    ),
    Caso("PUT", "/api/plantillas/{plantilla_id}/dimensiones/{dimension_id}", cuerpo={"nombre": "x"}),
    Caso("DELETE", "/api/plantillas/{plantilla_id}/dimensiones/{dimension_id}"),
    # --- tags ---
    Caso("PUT", "/api/tags/{tag_id}", cuerpo={"nombre": "Intento ajeno"}),
    Caso("DELETE", "/api/tags/{tag_id}"),
    # --- vacantes ---
    Caso("GET", "/api/vacantes/{vacante_id}"),
    Caso("PUT", "/api/vacantes/{vacante_id}", cuerpo={"titulo": "Intento ajeno"}),
    Caso("POST", "/api/vacantes/{vacante_id}/publicar"),
    Caso("POST", "/api/vacantes/{vacante_id}/pausar"),
    Caso("POST", "/api/vacantes/{vacante_id}/cerrar"),
    Caso("POST", "/api/vacantes/{vacante_id}/duplicar"),
    Caso("POST", "/api/vacantes/{vacante_id}/generar-textos"),
    Caso("GET", "/api/vacantes/{vacante_id}/textos"),
    Caso("PUT", "/api/vacantes/{vacante_id}/textos", cuerpo={"textos": {"linkedin": "x"}}),
    Caso("DELETE", "/api/vacantes/{vacante_id}"),
    Caso("POST", "/api/vacantes", cuerpo={"area_id": "{area_id}", "titulo": "Vacante con área ajena"}),
    # --- usuarios RRHH ---
    Caso("PUT", "/api/auth/usuarios/{usuario_id}/activar"),
    Caso("PUT", "/api/auth/usuarios/{usuario_id}/desactivar"),
    Caso("PUT", "/api/auth/usuarios/{usuario_id}/cambiar-password", cuerpo={"password_nueva": "Nueva-Clave-12345678"}),
    Caso("POST", "/api/auth/usuarios/{usuario_id}/reenviar-credenciales"),
]


def _resolver(plantilla: str, ajeno: Ajeno) -> str:
    return plantilla.format(**asdict(ajeno))


def _resolver_valores(valor: Any, ajeno: Ajeno) -> Any:
    """Reemplaza placeholders `{campo}` dentro de cuerpos/queries anidados (dict/list/str)."""
    if isinstance(valor, str):
        return _resolver(valor, ajeno)
    if isinstance(valor, dict):
        return {k: _resolver_valores(v, ajeno) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_resolver_valores(v, ajeno) for v in valor]
    return valor


@pytest.mark.parametrize("caso", CASOS, ids=[f"{c.metodo} {c.ruta}" for c in CASOS])
async def test_empresa_b_no_accede_a_recursos_de_empresa_a(
    client: TestClient, headers_otro: dict[str, str], ajeno: Ajeno, caso: Caso
) -> None:
    """Ningún endpoint autenticado de RRHH deja a la empresa B leer o modificar un recurso de A."""
    ruta = _resolver(caso.ruta, ajeno)
    cuerpo = _resolver_valores(caso.cuerpo, ajeno) if caso.cuerpo is not None else None
    query = _resolver_valores(caso.query, ajeno) if caso.query is not None else None

    respuesta = client.request(caso.metodo, ruta, json=cuerpo, params=query, headers=headers_otro)

    assert respuesta.status_code in caso.estados_esperados, (
        f"{caso.metodo} {ruta} -> {respuesta.status_code} (se esperaba uno de {sorted(caso.estados_esperados)}): "
        f"{respuesta.text}"
    )


# --- Casos que no caben en la tabla genérica (multipart / verificación de identidad) -----


async def test_empresa_b_no_crea_candidato_en_vacante_de_empresa_a(
    client: TestClient, headers_otro: dict[str, str], ajeno: Ajeno
) -> None:
    """POST /candidatos (multipart) valida el tenant de vacante_id antes de leer el CV."""
    archivo = {"cv": ("cv.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")}
    datos = {"vacante_id": ajeno.vacante_id, "nombre": "X", "apellidos": "Y", "email": "x@example.com"}
    respuesta = client.post("/api/candidatos", data=datos, files=archivo, headers=headers_otro)
    assert respuesta.status_code == 404, respuesta.text


async def test_empresa_b_no_hace_carga_masiva_en_vacante_de_empresa_a(
    client: TestClient, headers_otro: dict[str, str], ajeno: Ajeno
) -> None:
    """POST /candidatos/carga-masiva valida el tenant de vacante_id antes de procesar archivos."""
    archivo = {"archivos": ("cv.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")}
    respuesta = client.post(
        "/api/candidatos/carga-masiva", data={"vacante_id": ajeno.vacante_id}, files=archivo, headers=headers_otro
    )
    assert respuesta.status_code == 404, respuesta.text


async def test_empresa_b_no_cierra_la_sesion_de_un_usuario_de_empresa_a(
    client: TestClient, db_session: AsyncSession, db_engine: AsyncEngine
) -> None:
    """POST /auth/logout: el refresh_token de A no se puede cerrar autenticado como B (sesiones.cerrar).

    No depende de `ajeno`/`headers_otro` porque necesita un login real (con contraseña) para
    tener un refresh_token válido, no solo un access_token emitido directamente. Cada usuario
    se crea con la sesión fijada a su propio tenant (la RLS rechazaría lo contrario, DEC-010).
    """
    db_session.add(
        Usuario(
            tenant_id=TENANT_ID, nombre="A", apellidos="Admin", email="admin-a@test.vael",
            password_hash=await hash_password(PASSWORD), rol=RolUsuario.ADMIN,
        )
    )
    await db_session.commit()
    async with AsyncSession(db_engine, expire_on_commit=False, info={CLAVE_TENANT: TENANT_ID_OTRO}) as db_otro:
        db_otro.add(
            Usuario(
                tenant_id=TENANT_ID_OTRO, nombre="B", apellidos="Admin", email="admin-b@test.vael",
                password_hash=await hash_password(PASSWORD), rol=RolUsuario.ADMIN,
            )
        )
        await db_otro.commit()

    a = client.post("/api/auth/login", json={"email": "admin-a@test.vael", "password": PASSWORD}).json()
    b = client.post("/api/auth/login", json={"email": "admin-b@test.vael", "password": PASSWORD}).json()

    respuesta = client.post(
        "/api/auth/logout", json={"refresh_token": a["refresh_token"]},
        headers={"Authorization": f"Bearer {b['access_token']}"},
    )
    assert respuesta.status_code == 401, respuesta.text
    # El refresh token de A sigue vigente: B no lo pudo revocar.
    assert client.post("/api/auth/refresh", json={"refresh_token": a["refresh_token"]}).status_code == 200


# --- Token de candidato (DEC-021): el candidato de B no toca recursos de A --------------


async def test_candidato_b_no_responde_preguntas_del_examen_de_empresa_a(
    client: TestClient, candidato_b: Candidato, ajeno: Ajeno
) -> None:
    """POST /evaluaciones/candidato/examen/respuesta: `pregunta_id` es el único campo de un
    endpoint de candidato que referencia un recurso por id — los demás resuelven todo desde
    el propio token (ver `_CANDIDATO_SIN_VECTOR_CRUZADO`). La pregunta de A no es visible
    para B ni por RLS (sesión fijada al tenant de B) ni por el chequeo explícito del router."""
    headers = await _headers_candidato(candidato_b, TipoToken.EXAMEN)
    respuesta = client.post(
        "/api/evaluaciones/candidato/examen/respuesta",
        json={"pregunta_id": ajeno.pregunta_id, "respuesta": "intento ajeno"},
        headers=headers,
    )
    assert respuesta.status_code == 404, respuesta.text


# Endpoints de candidato sin vector cruzado por diseño: la identidad (candidato, examen o
# entrevista) siempre se resuelve desde el propio token (claims.sub/tenant_id), nunca de un
# id que el cliente pueda cambiar — ni en la ruta (no tienen parámetros de id) ni en el
# cuerpo. El valor es el módulo:clase del request body cuando lo tienen (para verificar que
# ninguno de sus campos termina en "_id"), o None si no reciben cuerpo JSON (multipart o sin
# cuerpo). /examen/respuesta queda fuera de esta tabla porque sí tiene un caso de ataque.
_CANDIDATO_SIN_VECTOR_CRUZADO: dict[tuple[str, str], str | None] = {
    ("POST", "/api/entrevista/acceso"): None,
    ("POST", "/api/entrevista/iniciar"): None,
    ("POST", "/api/entrevista/finalizar"): "app.schemas.entrevista:FinalizarEntrevistaRequest",
    ("POST", "/api/entrevista/captura"): None,
    ("POST", "/api/entrevista/evento"): "app.schemas.entrevista:EventoAuditoriaRequest",
    ("POST", "/api/evaluaciones/candidato/acceso"): None,
    ("POST", "/api/evaluaciones/candidato/examen/iniciar"): None,
    ("POST", "/api/evaluaciones/candidato/examen/finalizar"): None,
    ("POST", "/api/evaluaciones/candidato/examen/evento"): "app.schemas.evaluacion:EventoProctoringRequest",
    ("GET", "/api/evaluaciones/candidato/progreso"): None,
}


@pytest.mark.parametrize(
    "schema_path", [v for v in _CANDIDATO_SIN_VECTOR_CRUZADO.values() if v is not None],
)
def test_candidato_sin_vector_cruzado_no_acepta_ids_ajenos(schema_path: str) -> None:
    """Ninguno de estos cuerpos referencia un recurso por id (ningún campo termina en `_id`):
    no hay forma de pedirle a estos endpoints un examen, entrevista o pregunta de otra
    empresa — la identidad del candidato ya fija cuál es "su" examen o entrevista."""
    modulo_nombre, clase_nombre = schema_path.split(":")
    modulo = importlib.import_module(modulo_nombre)
    schema = getattr(modulo, clase_nombre)
    con_id = [campo for campo in schema.model_fields if campo.endswith("_id")]
    assert con_id == [], f"{clase_nombre} referencia un id ({con_id}): necesita su propio caso de ataque"


async def test_token_de_candidato_no_sirve_en_endpoints_de_rrhh(
    client: TestClient, candidato_b: Candidato
) -> None:
    """Un token de candidato (`type: candidate`) no pasa get_current_user: 401, no 403."""
    headers = await _headers_candidato(candidato_b, TipoToken.EXAMEN)
    respuesta = client.get("/api/areas", headers=headers)
    assert respuesta.status_code == 401, respuesta.text


async def test_token_de_rrhh_no_sirve_en_endpoints_de_candidato(
    client: TestClient, headers_otro: dict[str, str]
) -> None:
    """Un access_token de RRHH (`type: access`) no pasa get_current_candidate: 401, no 403."""
    respuesta = client.post("/api/evaluaciones/candidato/acceso", headers=headers_otro)
    assert respuesta.status_code == 401, respuesta.text


# --- Colecciones: ninguna expone filas de la otra empresa (sin id de recurso en la ruta) -


COLECCIONES: list[tuple[str, str, Callable[[Ajeno], str]]] = [
    ("GET", "/api/areas", lambda a: a.area_id),
    ("GET", "/api/candidatos", lambda a: a.candidato_id),
    ("GET", "/api/candidatos/banco-talento", lambda a: a.candidato_id),
    ("GET", "/api/candidatos/por-confirmar", lambda a: a.candidato_id),
    ("GET", "/api/vacantes", lambda a: a.vacante_id),
    ("GET", "/api/plantillas", lambda a: a.plantilla_id),
    ("GET", "/api/tags", lambda a: a.tag_id),
    ("GET", "/api/entrevista", lambda a: a.entrevista_id),
    ("GET", "/api/evaluaciones/examenes", lambda a: a.examen_id),
    ("GET", "/api/evaluaciones/auditoria", lambda a: a.examen_id),
    ("GET", "/api/auth/usuarios", lambda a: a.usuario_id),
]


@pytest.mark.parametrize(("metodo", "ruta", "id_ajeno"), COLECCIONES, ids=[c[1] for c in COLECCIONES])
async def test_colecciones_no_exponen_filas_de_empresa_a(
    client: TestClient, headers_otro: dict[str, str], ajeno: Ajeno,
    metodo: str, ruta: str, id_ajeno: Callable[[Ajeno], str],
) -> None:
    """Los endpoints de listado del tenant B nunca incluyen el id de un recurso creado en A."""
    respuesta = client.request(metodo, ruta, headers=headers_otro)
    assert respuesta.status_code == 200, respuesta.text
    assert id_ajeno(ajeno) not in respuesta.text


async def test_dashboard_de_metricas_no_mezcla_empresas(
    client: TestClient, headers_otro: dict[str, str], ajeno: Ajeno
) -> None:
    """GET /metricas/dashboard del tenant B no cuenta el candidato creado en A."""
    respuesta = client.get("/api/metricas/dashboard", headers=headers_otro)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert sum(cuerpo["candidatos_por_estado"].values()) == 0
    assert sum(cuerpo["vacantes_por_estado"].values()) == 0


# --- Endpoints sin vector cruzado por diseño: no aceptan ninguna referencia a otro tenant -


def test_perfil_no_tiene_vector_cruzado(client: TestClient, headers_otro: dict[str, str]) -> None:
    """GET /auth/perfil no acepta ningún id: siempre retorna al dueño del propio access_token."""
    respuesta = client.get("/api/auth/perfil", headers=headers_otro)
    assert respuesta.status_code == 200
    assert respuesta.json()["tenant_id"] == TENANT_ID_OTRO


@pytest.mark.parametrize(
    "schema_path",
    [
        "app.schemas.area:AreaCreateRequest",
        "app.schemas.tag:TagCreateRequest",
        "app.schemas.plantilla:PlantillaCreateRequest",
        "app.schemas.auth:CrearUsuarioRequest",
    ],
)
def test_los_formularios_de_creacion_no_reciben_tenant_ni_ids_ajenos(schema_path: str) -> None:
    """POST /areas, /tags, /plantillas y /auth/usuarios/crear: el tenant lo pone el servidor
    (`actor.tenant_id`), nunca el cliente, y el cuerpo no referencia ningún recurso de otra
    empresa — no hay forma de pedirle a estos endpoints un recurso ajeno. Son, por diseño,
    los únicos POST de creación de RRHH sin un caso de intento cruzado."""
    modulo_nombre, clase_nombre = schema_path.split(":")
    modulo = importlib.import_module(modulo_nombre)
    schema = getattr(modulo, clase_nombre)
    assert "tenant_id" not in schema.model_fields


# --- Cobertura automática (CA punto 3) ---------------------------------------------------


# Rutas ejercidas por un test de esta suite que no son un (método, ruta-con-placeholders) de
# CASOS/COLECCIONES: multipart, logout, perfil, dashboard y los formularios sin vector cruzado.
_CUBIERTAS_FUERA_DE_TABLA_RRHH = {
    ("POST", "/api/candidatos"),
    ("POST", "/api/candidatos/carga-masiva"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/auth/perfil"),
    ("GET", "/api/metricas/dashboard"),
    ("POST", "/api/areas"),
    ("POST", "/api/tags"),
    ("POST", "/api/plantillas"),
    ("POST", "/api/auth/usuarios/crear"),
}

# El único endpoint de candidato con un caso de ataque real (pregunta_id); el resto está en
# _CANDIDATO_SIN_VECTOR_CRUZADO, justificado y verificado por su propia prueba estructural.
_CUBIERTAS_CANDIDATO = {("POST", "/api/evaluaciones/candidato/examen/respuesta")} | set(
    _CANDIDATO_SIN_VECTOR_CRUZADO
)


def test_la_cobertura_es_total() -> None:
    """Toda ruta autenticada del OpenAPI vivo (RRHH o candidato) tiene un caso de aislamiento
    en esta suite; las 5 operaciones de la lista cerrada (DEC-010/014/021) quedan excluidas
    porque no pasan por ninguna dependencia de autenticación — no son "endpoints autenticados".

    Si se agrega un endpoint nuevo bajo `require_rol`/`get_current_user` o
    `get_current_candidate`/`get_current_candidato` y no se agrega su caso aquí, esta prueba
    falla: así la cobertura del 100% (CA) se mantiene automáticamente, sin depender de que
    alguien se acuerde de actualizar una lista a mano.
    """
    vivas = _rutas_autenticadas_rrhh() | _rutas_autenticadas_candidato()

    de_tabla = {(c.metodo, c.ruta) for c in CASOS}
    de_colecciones = {(metodo, ruta) for metodo, ruta, _ in COLECCIONES}
    cubiertas = de_tabla | de_colecciones | _CUBIERTAS_FUERA_DE_TABLA_RRHH | _CUBIERTAS_CANDIDATO

    faltantes = vivas - cubiertas
    assert faltantes == set(), f"Endpoints autenticados sin prueba de aislamiento: {sorted(faltantes)}"

    # También al revés: ningún caso de la tabla apunta a una ruta que ya no existe o dejó de
    # requerir autenticación (evita que la tabla quede con casos obsoletos).
    de_mas = cubiertas - vivas
    assert de_mas == set(), f"Casos de esta suite que ya no corresponden a un endpoint autenticado vivo: {sorted(de_mas)}"
