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
- TI-2026-001 (empresa A): candidatos con el proceso completo (CV, examen y entrevista),
  más que `top_candidatos_finalistas`, para demostrar el ranking y el lote de finalistas con
  datos reales (RF-A-14, RF-A-15, DEC-022); uno más con el examen rendido y sin entrevista,
  para el caso de proceso incompleto (doc 13, DEV-A-07).

Las decisiones de CV y examen de este script pasan por `decisiones.registrar_decision` con
`enviar_correos=False`: avanzan al candidato (estado, token) igual que un avance real, pero no
disparan el correo de la etapa siguiente. Sin esto, encender el entorno en AWS (doc 09) enviaría
correos reales por SES a direcciones `@example.com`.

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
from app.core.proctoring import CATALOGO_EVENTOS_PROCTORING
from app.core.scoring import calcular_score_final
from app.core.security import hash_password
from app.models.area import Area
from app.models.base import utcnow
from app.models.candidato import Candidato, ClasificacionIA, EstadoCandidato, NotaCandidato
from app.models.decision import EtapaDecision, TipoDecision
from app.models.entrevista import DimensionEvaluacion, EntrevistaIA, EstadoEntrevista, PlantillaEvaluacion
from app.models.evaluacion import EstadoExamen, EventoAuditoria, Examen
from app.models.usuario import RolUsuario, Usuario
from app.models.vacante import EstadoVacante, NivelExperiencia, Vacante
from app.scripts import generar_cvs
from app.scripts.crear_empresa import AbrirSesion, crear_empresa
from app.services import decisiones
from app.services.examen import registrar_evento

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

# Comentario de la IA por nivel de desempeño, reutilizado en las cinco dimensiones de la
# entrevista de cada candidato semilla (DEV-A-07): no llama a Gemini, igual que el resto de
# las semillas (el score del CV y de la empresa B tampoco pasan por la IA real).
_NIVEL_COMENTARIO = {
    "alto": "Respuesta sólida, con ejemplos concretos y buen manejo del tema.",
    "medio_alto": "Respuesta clara, con algunos detalles por profundizar.",
    "medio": "Respuesta correcta en lo general, con experiencia aún limitada.",
    "medio_bajo": "Respuesta superficial, con poca experiencia práctica en el tema.",
    "bajo": "Respuesta básica; evidencia poca experiencia práctica en el tema.",
}


@dataclass(frozen=True)
class CandidatoCompletoSemilla:
    """Candidato de TI-2026-001 con el proceso completo (CV, examen y entrevista), para
    demostrar en vivo el ranking y el lote de finalistas con datos reales (RF-A-14, RF-A-15,
    DEC-022, doc 13).
    """

    nombre: str
    apellidos: str
    email: str
    score_cv: int
    clasificacion: ClasificacionIA
    resumen: str
    habilidades: list[str]
    nota_examen: float
    eventos_examen: list[str]
    nivel_entrevista: str
    dimensiones_entrevista: dict[str, float]
    transcripcion: str
    evento_entrevista: str | None = None


@dataclass(frozen=True)
class CandidatoIncompletoSemilla:
    """Candidato de TI-2026-001 con el examen rendido pero sin entrevista: `score_final` queda
    nulo, así que el ranking lo muestra aparte (RF-A-14, doc 13)."""

    nombre: str
    apellidos: str
    email: str
    score_cv: int
    clasificacion: ClasificacionIA
    resumen: str
    habilidades: list[str]
    nota_examen: float


# `top_candidatos_finalistas` de TI-2026-001 es 5 (default, doc 05): siete candidatos completos
# dejan tres por encima del corte visibles por debajo también (CA de DEV-A-07). score_final se
# calcula con calcular_score_final (DEC-007), no se fija a mano.
CANDIDATOS_TI_COMPLETOS = [
    CandidatoCompletoSemilla(
        "Patricia", "Nolasco Vega", "patricia.nolasco@example.com", 90, ClasificacionIA.ALTAMENTE_RECOMENDADO,
        "Backend sólido en Python con FastAPI y PostgreSQL en producción.",
        ["Python", "FastAPI", "PostgreSQL", "Docker", "pytest"], 19.0, [], "alto",
        {"Claridad": 18, "Coherencia": 18, "Precisión técnica": 19, "Comunicación": 17, "Seguridad": 18},
        "EVA: Hola Patricia, bienvenida a tu entrevista para Desarrollador Backend Python. "
        "Cuéntame sobre tu experiencia con FastAPI.\n"
        "Candidato: He construido APIs REST en producción con FastAPI, usando Pydantic para "
        "validación y SQLModel con PostgreSQL, incluyendo migraciones con Alembic.\n"
        "EVA: ¿Cómo manejarías una consulta lenta sobre una tabla con millones de filas?\n"
        "Candidato: Revisaría el plan de ejecución con EXPLAIN ANALYZE, agregaría los índices "
        "adecuados y, si hace falta, paginaría con cursores en vez de OFFSET.\n"
        "EVA: ¿Qué estrategia usas para probar tu código?\n"
        "Candidato: Pytest con fixtures para la base de datos de prueba, cobertura de los casos "
        "límite y tests de integración contra los endpoints reales.\n"
        "EVA: ¿Cómo asegurarías la contención de concurrencia al modificar un mismo registro?\n"
        "Candidato: Con bloqueo optimista usando una columna de versión, o una transacción con "
        "SELECT FOR UPDATE cuando el caso lo exige.",
    ),
    CandidatoCompletoSemilla(
        "Marco", "Villanueva Ríos", "marco.villanueva@example.com", 85, ClasificacionIA.ALTAMENTE_RECOMENDADO,
        "Cuatro años con Django y PostgreSQL; migrando a FastAPI en su último proyecto.",
        ["Python", "PostgreSQL", "Docker"], 18.0, ["perdida_foco"], "medio_alto",
        {"Claridad": 17, "Coherencia": 16, "Precisión técnica": 17, "Comunicación": 16, "Seguridad": 15},
        "EVA: Hola Marco, cuéntame sobre tu experiencia con Python y bases de datos relacionales.\n"
        "Candidato: Trabajé con Django y PostgreSQL por cuatro años, y en el último proyecto "
        "migramos parte del backend a FastAPI.\n"
        "EVA: ¿Cómo estructurarías un proyecto FastAPI de tamaño mediano?\n"
        "Candidato: Separaría por dominios con routers, servicios y modelos, y usaría Pydantic "
        "para los schemas de entrada y salida.\n"
        "EVA: ¿Qué harías si un endpoint empieza a responder lento en producción?\n"
        "Candidato: Revisaría los logs y las métricas primero, y si es la base de datos, "
        "buscaría consultas N+1 o falta de índices.\n"
        "EVA: ¿Usas Docker en tu flujo de trabajo?\n"
        "Candidato: Sí, contenerizo la app y la base de datos de desarrollo con docker-compose.",
    ),
    CandidatoCompletoSemilla(
        "Carla", "Espinoza Durand", "carla.espinoza@example.com", 78, ClasificacionIA.RECOMENDADO,
        "Servicios internos con Flask, migrando uno a FastAPI por la validación automática.",
        ["Python", "PostgreSQL"], 17.0, ["cambio_ventana", "perdida_foco"], "medio",
        {"Claridad": 15, "Coherencia": 15, "Precisión técnica": 16, "Comunicación": 15, "Seguridad": 14},
        "EVA: Hola Carla, hablemos de tu experiencia técnica. ¿Qué proyectos has hecho con Python?\n"
        "Candidato: Desarrollé servicios internos con Flask y después migré uno a FastAPI por "
        "el tema de la validación automática.\n"
        "EVA: ¿Cómo manejas los errores en una API REST?\n"
        "Candidato: Devuelvo códigos de estado adecuados y un mensaje claro, aunque reconozco "
        "que no siempre centralizo el manejo de excepciones.\n"
        "EVA: ¿Qué sabes de PostgreSQL?\n"
        "Candidato: Uso consultas básicas y algo de índices, pero no he trabajado mucho con "
        "particionamiento ni replicación.\n"
        "EVA: ¿Has usado pytest?\n"
        "Candidato: Sí, para pruebas unitarias simples, aunque me falta experiencia con mocks "
        "más complejos.",
    ),
    CandidatoCompletoSemilla(
        "Diego", "Farfán Rioja", "diego.farfan@example.com", 74, ClasificacionIA.RECOMENDADO,
        "Backend principalmente en Java; empezando con Python y FastAPI en un proyecto personal.",
        ["Python", "Docker"], 16.0, ["copy_paste", "click_derecho"], "medio_bajo",
        {"Claridad": 14, "Coherencia": 14, "Precisión técnica": 15, "Comunicación": 14, "Seguridad": 13},
        "EVA: Hola Diego, cuéntame sobre tu experiencia con Python en el backend.\n"
        "Candidato: Trabajé principalmente con Java, pero en los últimos meses empecé a usar "
        "Python y FastAPI en un proyecto personal.\n"
        "EVA: ¿Qué diferencias notas entre ambos lenguajes para construir una API?\n"
        "Candidato: Python es más rápido de escribir, pero todavía me cuesta el tipado opcional "
        "y async/await.\n"
        "EVA: ¿Cómo conectarías FastAPI con PostgreSQL?\n"
        "Candidato: Usaría SQLAlchemy o SQLModel, aunque solo lo he probado en tutoriales, no "
        "en producción.\n"
        "EVA: ¿Conoces Docker?\n"
        "Candidato: Lo he usado para levantar contenedores básicos, pero no he escrito un "
        "Dockerfile desde cero.",
        evento_entrevista="sin_rostro",
    ),
    CandidatoCompletoSemilla(
        "Brenda", "Quispe Tello", "brenda.quispe@example.com", 70, ClasificacionIA.RECOMENDADO,
        "Experiencia principal en PHP, con algo de Python en scripts de automatización.",
        ["Python"], 15.0, ["devtools", "copy_paste", "cambio_ventana"], "medio_bajo",
        {"Claridad": 13, "Coherencia": 13, "Precisión técnica": 14, "Comunicación": 13, "Seguridad": 12},
        "EVA: Hola Brenda, hablemos de tu experiencia como desarrolladora.\n"
        "Candidato: He trabajado principalmente con PHP y algo de Python en scripts de "
        "automatización.\n"
        "EVA: ¿Has construido alguna API con FastAPI o Flask?\n"
        "Candidato: No he construido una API completa, pero he hecho pequeños endpoints de "
        "prueba siguiendo tutoriales.\n"
        "EVA: ¿Qué sabes sobre pruebas automatizadas?\n"
        "Candidato: Conozco pytest de nombre, pero no lo he aplicado en un proyecto real todavía.\n"
        "EVA: ¿Cómo describirías tu experiencia con bases de datos relacionales?\n"
        "Candidato: Uso consultas SQL básicas, principalmente a través de un ORM, sin "
        "profundizar mucho en el motor.",
    ),
    CandidatoCompletoSemilla(
        "Álvaro", "Medina Ponce", "alvaro.medina@example.com", 66, ClasificacionIA.REQUIERE_REVISION,
        "Python como segundo lenguaje, usado sobre todo para scripts cortos.",
        ["Python"], 14.0, ["devtools", "copy_paste", "click_derecho"], "bajo",
        {"Claridad": 12, "Coherencia": 12, "Precisión técnica": 13, "Comunicación": 12, "Seguridad": 11},
        "EVA: Hola Álvaro, cuéntame sobre tu experiencia con Python.\n"
        "Candidato: Es mi segundo lenguaje, lo uso sobre todo para scripts cortos, no para "
        "backends completos.\n"
        "EVA: ¿Has trabajado con FastAPI o algún framework similar?\n"
        "Candidato: No directamente; he visto ejemplos, pero no he construido nada en producción.\n"
        "EVA: ¿Qué conoces sobre PostgreSQL?\n"
        "Candidato: Lo básico, consultas simples; no he trabajado con migraciones ni índices.\n"
        "EVA: ¿Usas control de versiones y pruebas automatizadas?\n"
        "Candidato: Uso Git, pero no tengo experiencia con pruebas automatizadas todavía.",
        evento_entrevista="multiples_voces",
    ),
    CandidatoCompletoSemilla(
        "Yolanda", "Chumpitaz Rau", "yolanda.chumpitaz@example.com", 60, ClasificacionIA.REQUIERE_REVISION,
        "Experiencia principal en soporte técnico, con algo de scripting en Python.",
        ["Python"], 14.0, ["devtools", "copy_paste", "click_derecho", "cambio_ventana"], "bajo",
        {"Claridad": 11, "Coherencia": 11, "Precisión técnica": 12, "Comunicación": 11, "Seguridad": 10},
        "EVA: Hola Yolanda, cuéntame sobre tu experiencia técnica.\n"
        "Candidato: Mi experiencia es sobre todo en soporte técnico, con algo de scripting en "
        "Python.\n"
        "EVA: ¿Has construido alguna API REST?\n"
        "Candidato: No he construido una API desde cero, solo he consumido algunas desde el "
        "frontend.\n"
        "EVA: ¿Conoces PostgreSQL o alguna base de datos relacional?\n"
        "Candidato: Conozco conceptos básicos de SQL de un curso introductorio.\n"
        "EVA: ¿Qué harías si un servicio en producción deja de responder?\n"
        "Candidato: Reiniciaría el servicio y revisaría los logs, aunque no tengo mucha "
        "experiencia en ese escenario.",
    ),
]

CANDIDATO_TI_INCOMPLETO = CandidatoIncompletoSemilla(
    "Jorge", "Salcedo Peña", "jorge.salcedo@example.com", 68, ClasificacionIA.RECOMENDADO,
    "Dos años con Python en tareas de automatización; primera vez postulando a un rol backend.",
    ["Python", "Docker"], 15.0,
)


def _dimensiones_entrevista_semilla(
    dimensiones: list[DimensionEvaluacion], notas: dict[str, float], nivel: str
) -> tuple[dict[str, Any], float]:
    """Arma `dimensiones_json` y la nota de la entrevista con la misma fórmula de
    `entrevista_ia.analizar_entrevista` (promedio ponderado por el peso de cada dimensión,
    normalizado a su `puntaje_maximo` y escalado a 0-20), sin llamar a Gemini — igual que el
    resto de las semillas no llama a la IA real para el análisis del CV.
    """
    comentario = _NIVEL_COMENTARIO[nivel]
    dimensiones_json: dict[str, Any] = {}
    suma_ponderada = 0.0
    suma_pesos = 0.0
    for dimension in dimensiones:
        nota = notas[dimension.nombre]
        dimensiones_json[dimension.nombre] = {
            "nota": nota, "puntaje_maximo": dimension.puntaje_maximo, "peso": dimension.peso, "comentario": comentario,
        }
        if dimension.puntaje_maximo > 0:
            suma_ponderada += (nota / dimension.puntaje_maximo) * dimension.peso
            suma_pesos += dimension.peso
    nota_final = round((suma_ponderada / suma_pesos) * 20, 2) if suma_pesos > 0 else 0.0
    return dimensiones_json, nota_final


async def _avanzar_cv_y_examen(
    db: AsyncSession, tenant_id: str, vacante: Vacante, admin: Usuario,
    nombre: str, apellidos: str, email: str, score_cv: int, clasificacion: ClasificacionIA,
    resumen: str, habilidades: list[str], nota_examen: float, eventos_examen: list[str],
) -> tuple[Candidato, Examen]:
    """Crea (o recupera) un candidato de TI-2026-001 y lo hace avanzar en CV y examen a través
    del servicio de decisiones, para no romper el invariante del OE3 (TST-C-04), igual que
    `_datos_empresa_b`.
    """
    filtro = (Candidato.tenant_id == tenant_id, Candidato.vacante_id == vacante.id, Candidato.email == email)
    candidato = (await db.exec(select(Candidato).where(*filtro))).first()
    if candidato is None:
        candidato = Candidato(
            tenant_id=tenant_id, vacante_id=vacante.id, nombre=nombre, apellidos=apellidos, email=email,
            estado=EstadoCandidato.CV_POR_CONFIRMAR, score_cv=score_cv, clasificacion_ia=clasificacion,
            resumen_ia=resumen, habilidades_detectadas=habilidades,
        )
        db.add(candidato)
        await db.commit()
        await db.refresh(candidato)

    if candidato.estado == EstadoCandidato.CV_POR_CONFIRMAR:
        solicitud = decisiones.DecisionSolicitada(EtapaDecision.CV, TipoDecision.AVANZAR)
        await decisiones.registrar_decision(candidato.id, solicitud, admin, db, enviar_correos=False)

    examen = (await db.exec(select(Examen).where(Examen.candidato_id == candidato.id))).first()
    if examen is None:
        examen = Examen(tenant_id=tenant_id, candidato_id=candidato.id, vacante_id=vacante.id, estado=EstadoExamen.FINALIZADO, nota=nota_examen)
        db.add(examen)
        candidato.estado = EstadoCandidato.EXAMEN_POR_CONFIRMAR
        db.add(candidato)
        await db.commit()
        await db.refresh(examen)
        for tipo in eventos_examen:
            await registrar_evento(examen.id, tenant_id, tipo, None, db)

    if candidato.estado == EstadoCandidato.EXAMEN_POR_CONFIRMAR:
        solicitud = decisiones.DecisionSolicitada(EtapaDecision.EXAMEN, TipoDecision.AVANZAR)
        await decisiones.registrar_decision(candidato.id, solicitud, admin, db, enviar_correos=False)

    return candidato, examen


async def _candidatos_proceso_completo_ti(db: AsyncSession, tenant_id: str, vacante: Vacante, admin: Usuario) -> None:
    """TI-2026-001: siete candidatos con el proceso completo (más que `top_candidatos_finalistas`,
    5 por defecto) y uno con el examen rendido sin entrevista, para el ranking y el lote de
    finalistas con datos reales (RF-A-14, RF-A-15, DEC-022, doc 13).
    """
    plantilla = (await db.exec(
        select(PlantillaEvaluacion).where(PlantillaEvaluacion.tenant_id == tenant_id, PlantillaEvaluacion.nombre == "Técnico Estándar")
    )).first()
    dimensiones: list[DimensionEvaluacion] = []
    if plantilla is not None:
        dimensiones = list((await db.exec(
            select(DimensionEvaluacion).where(DimensionEvaluacion.plantilla_id == plantilla.id)
        )).all())

    for datos in CANDIDATOS_TI_COMPLETOS:
        candidato, examen = await _avanzar_cv_y_examen(
            db, tenant_id, vacante, admin, datos.nombre, datos.apellidos, datos.email, datos.score_cv,
            datos.clasificacion, datos.resumen, datos.habilidades, datos.nota_examen, datos.eventos_examen,
        )

        if (await db.exec(select(EntrevistaIA).where(EntrevistaIA.candidato_id == candidato.id))).first() is not None:
            continue

        dimensiones_json, nota_entrevista = _dimensiones_entrevista_semilla(
            dimensiones, datos.dimensiones_entrevista, datos.nivel_entrevista
        )
        entrevista = EntrevistaIA(
            tenant_id=tenant_id, candidato_id=candidato.id, vacante_id=vacante.id,
            plantilla_id=plantilla.id if plantilla else None, estado=EstadoEntrevista.FINALIZADA,
            nota=nota_entrevista, transcripcion=datos.transcripcion, duracion_minutos=18,
            dimensiones_json=dimensiones_json, fecha_inicio=utcnow(), fecha_fin=utcnow(),
        )
        db.add(entrevista)
        await db.flush()
        if datos.evento_entrevista:
            severidad, _ = CATALOGO_EVENTOS_PROCTORING[datos.evento_entrevista]
            db.add(EventoAuditoria(tenant_id=tenant_id, entrevista_id=entrevista.id, tipo=datos.evento_entrevista, severidad=severidad))

        candidato.estado = EstadoCandidato.ENTREVISTA_REALIZADA
        candidato.score_final = calcular_score_final(candidato.score_cv, examen.nota, nota_entrevista)
        candidato.updated_at = utcnow()
        db.add(candidato)
        await db.commit()

    incompleto = CANDIDATO_TI_INCOMPLETO
    await _avanzar_cv_y_examen(
        db, tenant_id, vacante, admin, incompleto.nombre, incompleto.apellidos, incompleto.email,
        incompleto.score_cv, incompleto.clasificacion, incompleto.resumen, incompleto.habilidades,
        incompleto.nota_examen, [],
    )


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
        await decisiones.registrar_decision(con_examen.id, solicitud, admin, db, enviar_correos=False)
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
                if empresa == EMPRESA_A:
                    vacante_ti = next(v for v in vacantes if v.codigo == "TI-2026-001")
                    await _candidatos_proceso_completo_ti(db, tenant_id, vacante_ti, alta.administrador)
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
