"""Carga los datos semilla del doc 13 (DEV-C-03). Idempotente: ejecutarlo dos veces no duplica.

Uso (con SEED_PASSWORD o SEED_PASSWORD_<ROL> definidas; nunca van en el repositorio):

    python -m app.scripts.semillas

- Empresas A (Andina Servicios) y B (Pacífico Logística), creadas con el script de alta
  (DEC-015), con un usuario por rol en A y un reclutador inactivo para RF-A-01.
- Áreas, las cuatro plantillas predefinidas del doc 05 y las cinco vacantes.
- Los 20 CV de la empresa A como PDF en backend/seeds/cvs/ (se registran desde la app
  para medir el OE1; el script no los analiza).
- Empresa B: tres candidatos con su análisis, uno con examen y una nota interna, para que
  TST-C-01 tenga cada tipo de recurso que la empresa A nunca debe ver.

Busca por claves naturales: correo del usuario, código del área, código de la vacante,
nombre de la plantilla y correo del candidato.
"""
import asyncio
import sys
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import con_tenant, sesion_con_tenant
from app.core.security import hash_password
from app.models.area import Area
from app.models.candidato import Candidato, ClasificacionIA, EstadoCandidato, NotaCandidato
from app.models.decision import EtapaDecision, TipoDecision
from app.models.entrevista import DimensionEvaluacion, PlantillaEvaluacion
from app.models.evaluacion import EstadoExamen, Examen
from app.models.usuario import RolUsuario, Usuario
from app.models.vacante import EstadoVacante, NivelExperiencia, Vacante
from app.scripts import generar_cvs
from app.scripts.crear_empresa import AbrirSesion, crear_empresa
from app.services import decisiones

EMPRESA_A = "Andina Servicios S.A.C."
EMPRESA_B = "Pacífico Logística S.A.C."

# (correo, rol, nombre, apellidos, activo)
USUARIOS_A = [
    ("reclutador@andina.example.com", RolUsuario.RECLUTADOR, "Rocío", "Huertas Lazo", True),
    ("evaluador@andina.example.com", RolUsuario.EVALUADOR, "Ernesto", "Valdivia Prado", True),
    ("gerente@andina.example.com", RolUsuario.GERENTE, "Gisela", "Montes Ruiz", True),
    ("inactivo@andina.example.com", RolUsuario.RECLUTADOR, "Iván", "Cáceres Soto", False),
]
USUARIOS_B = [("reclutador@pacifico.example.com", RolUsuario.RECLUTADOR, "Raúl", "Paz Linares", True)]

# (empresa, nombre, código, instrucción de IA)
AREAS = [
    (EMPRESA_A, "Tecnología", "TI", "Valorar la profundidad técnica demostrable y los proyectos verificables"),
    (EMPRESA_A, "Comercial", "VEN", "Valorar la experiencia en ventas, el logro de metas y la comunicación"),
    (EMPRESA_A, "Operaciones", "OPE", "Valorar la experiencia en procesos, logística y mejora continua"),
    (EMPRESA_B, "Logística", "LOG", None),
]

# Plantillas predefinidas del doc 05: (nombre, [(dimensión, peso)])
PLANTILLAS = [
    ("Técnico Estándar", [("Claridad", 20), ("Coherencia", 20), ("Precisión técnica", 30), ("Comunicación", 20), ("Seguridad", 10)]),
    ("Comercial", [("Persuasión", 30), ("Escucha activa", 20), ("Orientación a resultados", 25), ("Manejo de objeciones", 25)]),
    ("Liderazgo", [("Visión", 25), ("Gestión de equipos", 25), ("Decisiones", 25), ("Comunicación ejecutiva", 25)]),
    ("Creativo", [("Originalidad", 30), ("Pensamiento divergente", 25), ("Argumentación", 25), ("Adaptabilidad", 20)]),
]


@dataclass(frozen=True)
class VacanteSemilla:
    empresa: str
    area: str
    codigo: str
    titulo: str
    nivel: NivelExperiencia
    estado: EstadoVacante
    confidencial: bool = False
    requisitos: str | None = None
    habilidades: list[str] = field(default_factory=list)


VACANTES = [
    VacanteSemilla(
        EMPRESA_A, "TI", "TI-2026-001", "Desarrollador Backend Python", NivelExperiencia.SEMI_SENIOR,
        EstadoVacante.ABIERTA, requisitos="3 años o más con Python y una base de datos relacional",
        habilidades=["Python", "FastAPI", "PostgreSQL", "Docker", "pytest"],
    ),
    VacanteSemilla(
        EMPRESA_A, "VEN", "VEN-2026-001", "Ejecutivo Comercial", NivelExperiencia.JUNIOR,
        EstadoVacante.ABIERTA, requisitos="1 año o más en ventas con metas",
        habilidades=["Venta consultiva", "Negociación", "CRM"],
    ),
    VacanteSemilla(EMPRESA_A, "OPE", "OPE-2026-001", "Analista de Operaciones", NivelExperiencia.JUNIOR, EstadoVacante.BORRADOR),
    VacanteSemilla(
        EMPRESA_A, "TI", "TI-2026-002", "Desarrollador Frontend (confidencial)", NivelExperiencia.JUNIOR,
        EstadoVacante.ABIERTA, confidencial=True, habilidades=["React", "TypeScript"],
    ),
    VacanteSemilla(EMPRESA_B, "LOG", "LOG-2026-001", "Coordinador Logístico", NivelExperiencia.SEMI_SENIOR, EstadoVacante.ABIERTA),
]

# Empresa B: (nombre, apellidos, correo, score, clasificación)
CANDIDATOS_B = [
    ("Mario", "Linares Peña", "mario.linares@example.com", 82, ClasificacionIA.RECOMENDADO),
    ("Elena", "Vidal Torres", "elena.vidal@example.com", 45, ClasificacionIA.REQUIERE_REVISION),
    ("Hugo", "Sánchez Mora", "hugo.sanchez@example.com", 74, ClasificacionIA.RECOMENDADO),
]


class ErrorSemillas(Exception):
    """Falta configuración para cargar las semillas."""


def password_de(rol: RolUsuario) -> str:
    """Contraseña semilla del rol: SEED_PASSWORD_<ROL> o, si no está, SEED_PASSWORD."""
    valor = getattr(settings, f"seed_password_{rol.value}") or settings.seed_password
    if not valor:
        raise ErrorSemillas(f"Define SEED_PASSWORD_{rol.value.upper()} o SEED_PASSWORD en el entorno")
    return valor


async def _usuario(db: AsyncSession, tenant_id: str, datos: tuple[str, RolUsuario, str, str, bool]) -> Usuario:
    email, rol, nombre, apellidos, activo = datos
    existente = (await db.exec(select(Usuario).where(Usuario.tenant_id == tenant_id, Usuario.email == email))).first()
    if existente is not None:
        return existente
    usuario = Usuario(
        tenant_id=tenant_id, nombre=nombre, apellidos=apellidos, email=email,
        password_hash=await hash_password(password_de(rol)), rol=rol, activo=activo,
    )
    db.add(usuario)
    await db.flush()
    return usuario


async def _area(db: AsyncSession, tenant_id: str, nombre: str, codigo: str, instruccion: str | None) -> Area:
    existente = (await db.exec(select(Area).where(Area.tenant_id == tenant_id, Area.codigo_corto == codigo))).first()
    if existente is not None:
        return existente
    area = Area(tenant_id=tenant_id, nombre=nombre, codigo_corto=codigo, instruccion_ia=instruccion)
    db.add(area)
    await db.flush()
    return area


async def _plantilla(db: AsyncSession, tenant_id: str, nombre: str, dimensiones: list[tuple[str, int]]) -> None:
    filtro = (PlantillaEvaluacion.tenant_id == tenant_id, PlantillaEvaluacion.nombre == nombre)
    if (await db.exec(select(PlantillaEvaluacion).where(*filtro))).first() is not None:
        return
    plantilla = PlantillaEvaluacion(tenant_id=tenant_id, nombre=nombre)
    db.add(plantilla)
    await db.flush()
    db.add_all(
        DimensionEvaluacion(tenant_id=tenant_id, plantilla_id=plantilla.id, nombre=dimension, peso=peso)
        for dimension, peso in dimensiones
    )


async def _vacante(db: AsyncSession, tenant_id: str, semilla: VacanteSemilla, areas: dict[str, Area]) -> Vacante:
    existente = (await db.exec(select(Vacante).where(Vacante.codigo == semilla.codigo))).first()
    if existente is not None:
        return existente
    vacante = Vacante(
        tenant_id=tenant_id, area_id=areas[semilla.area].id, codigo=semilla.codigo, titulo=semilla.titulo,
        nivel_experiencia=semilla.nivel, estado=semilla.estado, confidencial=semilla.confidencial,
        requisitos=semilla.requisitos, habilidades=semilla.habilidades,
    )
    db.add(vacante)
    await db.flush()
    return vacante


async def _datos_empresa_b(db: AsyncSession, tenant_id: str, vacante: Vacante, admin: Usuario) -> None:
    """Tres candidatos con análisis; el tercero avanza en CV por decisión humana y rinde el examen."""
    candidatos: list[Candidato] = []
    for nombre, apellidos, email, score, clasificacion in CANDIDATOS_B:
        filtro = (Candidato.tenant_id == tenant_id, Candidato.vacante_id == vacante.id, Candidato.email == email)
        candidato = (await db.exec(select(Candidato).where(*filtro))).first()
        if candidato is None:
            candidato = Candidato(
                tenant_id=tenant_id, vacante_id=vacante.id, nombre=nombre, apellidos=apellidos, email=email,
                estado=EstadoCandidato.CV_POR_CONFIRMAR, score_cv=score, clasificacion_ia=clasificacion,
                resumen_ia=f"Perfil de prueba de la empresa testigo ({clasificacion.value}).",
                habilidades_detectadas=["Gestión de almacenes", "Excel"],
            )
            db.add(candidato)
            await db.flush()
        candidatos.append(candidato)

    if (await db.exec(select(NotaCandidato).where(NotaCandidato.candidato_id == candidatos[0].id))).first() is None:
        db.add(NotaCandidato(tenant_id=tenant_id, candidato_id=candidatos[0].id, autor_id=admin.id, contenido="Nota interna de la empresa testigo"))
    await db.commit()

    con_examen = candidatos[2]
    if con_examen.estado == EstadoCandidato.CV_POR_CONFIRMAR:
        # Pasa por el servicio de decisiones para no romper el invariante del OE3 (TST-C-04).
        solicitud = decisiones.DecisionSolicitada(EtapaDecision.CV, TipoDecision.AVANZAR)
        await decisiones.registrar_decision(con_examen.id, solicitud, admin, db)
    if (await db.exec(select(Examen).where(Examen.candidato_id == con_examen.id))).first() is None:
        db.add(Examen(tenant_id=tenant_id, candidato_id=con_examen.id, vacante_id=vacante.id, estado=EstadoExamen.FINALIZADO, nota=14.0))
        db.add(con_examen)
        con_examen.estado = EstadoCandidato.EXAMEN_POR_CONFIRMAR
        await db.commit()


async def cargar(abrir_sesion: AbrirSesion = sesion_con_tenant, generar_pdfs: bool = True) -> dict[str, Any]:
    """Carga todas las semillas y retorna un resumen por empresa."""
    administradores = {
        EMPRESA_A: await crear_empresa(
            EMPRESA_A, "admin@andina.example.com", email_contacto="datos@andina.example.com",
            password=password_de(RolUsuario.ADMIN), enviar_credenciales=False, abrir_sesion=abrir_sesion,
        ),
        EMPRESA_B: await crear_empresa(
            EMPRESA_B, "admin@pacifico.example.com", email_contacto="datos@pacifico.example.com",
            password=password_de(RolUsuario.ADMIN), enviar_credenciales=False, abrir_sesion=abrir_sesion,
        ),
    }
    resumen: dict[str, Any] = {}
    for empresa, usuarios in ((EMPRESA_A, USUARIOS_A), (EMPRESA_B, USUARIOS_B)):
        alta = administradores[empresa]
        tenant_id = alta.tenant_id
        with con_tenant(tenant_id):
            async with abrir_sesion(tenant_id) as db:
                for datos in usuarios:
                    await _usuario(db, tenant_id, datos)
                areas = {
                    codigo: await _area(db, tenant_id, nombre, codigo, instruccion)
                    for emp, nombre, codigo, instruccion in AREAS
                    if emp == empresa
                }
                if empresa == EMPRESA_A:
                    for nombre, dimensiones in PLANTILLAS:
                        await _plantilla(db, tenant_id, nombre, dimensiones)
                vacantes = [await _vacante(db, tenant_id, v, areas) for v in VACANTES if v.empresa == empresa]
                await db.commit()
                if empresa == EMPRESA_B:
                    await _datos_empresa_b(db, tenant_id, vacantes[0], alta.administrador)
        resumen[empresa] = {"tenant_id": tenant_id, "vacantes": [v.codigo for v in vacantes]}

    if generar_pdfs:
        resumen["cvs"] = len(generar_cvs.generar())
    return resumen


def main() -> int:
    try:
        resumen = asyncio.run(cargar())
    except ErrorSemillas as error:
        print(f"No se cargaron las semillas: {error}", file=sys.stderr)
        return 1
    for empresa in (EMPRESA_A, EMPRESA_B):
        datos = resumen[empresa]
        print(f"{empresa} ({datos['tenant_id']}): vacantes {', '.join(datos['vacantes'])}", file=sys.stderr)
    print(f"{resumen['cvs']} CV en {generar_cvs.DIRECTORIO_PDF}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
