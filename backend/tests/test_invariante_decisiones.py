"""Invariante del OE3 (TST-C-04, HU-15): ningún candidato llega a un estado de avance o de
descarte sin su fila en decisiones_candidato (DEC-009).

Dos comprobaciones:
- Estática: ningún módulo de la app asigna a mano un estado de decisión humana; solo el
  servicio de decisiones los alcanza, a través de su tabla ESTADO_RESULTANTE.
- Dinámica: tras recorrer el proceso completo por la API, la consulta documentada del
  indicador (docs/metricas/oe3_registro_decisiones.sql) da 100 % en cada etapa y 0
  decisiones contrarias sin justificación. La misma consulta detecta una violación.
"""
import ast
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.candidato import Candidato, EstadoCandidato
from app.models.decision import DecisionCandidato, EtapaDecision, TipoDecision
from app.models.usuario import RolUsuario, Usuario
from app.services.decisiones import ESTADOS_DE_DECISION_HUMANA
from tests.conftest import TENANT_ID
from tests.test_decisiones import _candidato, _decidir, _examen, _vacante, enviados  # noqa: F401

RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIO_APP = RAIZ / "backend" / "app"
CONSULTA_OE3 = RAIZ / "docs" / "metricas" / "oe3_registro_decisiones.sql"

_NOMBRES_DE_DECISION = {estado.name for estado in ESTADOS_DE_DECISION_HUMANA}


def _es_estado_de_decision(nodo: ast.AST) -> bool:
    """True si el nodo es `EstadoCandidato.<estado de decisión humana>`."""
    return (
        isinstance(nodo, ast.Attribute)
        and isinstance(nodo.value, ast.Name)
        and nodo.value.id == "EstadoCandidato"
        and nodo.attr in _NOMBRES_DE_DECISION
    )


def test_ningun_modulo_asigna_a_mano_un_estado_de_decision() -> None:
    """Ni `x.estado = EstadoCandidato.CV_APROBADO` ni `Candidato(estado=...)` fuera de las decisiones."""
    hallazgos: list[str] = []
    for archivo in sorted(DIRECTORIO_APP.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign) and _es_estado_de_decision(nodo.value):
                if any(isinstance(t, ast.Attribute) and t.attr == "estado" for t in nodo.targets):
                    hallazgos.append(f"{archivo.relative_to(DIRECTORIO_APP)}:{nodo.lineno}")
            if isinstance(nodo, ast.keyword) and nodo.arg == "estado" and _es_estado_de_decision(nodo.value):
                hallazgos.append(f"{archivo.relative_to(DIRECTORIO_APP)}:{nodo.value.lineno}")
    assert hallazgos == [], f"Estados de decisión asignados fuera del servicio de decisiones: {hallazgos}"


def test_ninguna_decision_se_edita_ni_se_borra() -> None:
    """DEC-009 punto 2 (RF-A-12): decisiones_candidato es de solo inserción. Ningún
    `await db.delete(...)` de la app apunta a una variable de decisión; revertir es insertar
    una fila nueva con `reemplaza_a` (ver `registrar_decision`), nunca editar la anterior."""
    hallazgos: list[str] = []
    for archivo in sorted(DIRECTORIO_APP.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "delete"):
                continue
            for arg in nodo.args:
                if isinstance(arg, ast.Name) and "decision" in arg.id.lower():
                    hallazgos.append(f"{archivo.relative_to(DIRECTORIO_APP)}:{nodo.lineno}")
    assert hallazgos == [], f"Posibles eliminaciones de decisiones_candidato: {hallazgos}"


async def test_vael_app_no_puede_editar_ni_borrar_decisiones(db_session: AsyncSession) -> None:
    """RF-A-12/DEC-009, reforzado en la base de datos (no solo por convención del código):
    `vael_app` conserva SELECT e INSERT sobre decisiones_candidato, pero no UPDATE ni DELETE
    (migración `c8d9e0f1a2b3`; `crear_roles.py` reafirma la revocación en cada ejecución)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, sufijo="permiso-bd")
    usuario = Usuario(
        tenant_id=TENANT_ID, nombre="Test", apellidos="Permisos", email="permisos-bd@test.vael",
        password_hash="no-usado", rol=RolUsuario.ADMIN,
    )
    db_session.add(usuario)
    await db_session.flush()

    decision = DecisionCandidato(
        tenant_id=TENANT_ID, candidato_id=candidato.id, etapa=EtapaDecision.CV, decision=TipoDecision.AVANZAR,
        decidido_por=usuario.id,
    )
    db_session.add(decision)
    await db_session.commit()  # INSERT: funciona
    decision_id = decision.id  # capturado antes de cualquier rollback (evita un refresh expirado)

    leida = (await db_session.exec(select(DecisionCandidato).where(DecisionCandidato.id == decision_id))).one()
    assert leida.decision == TipoDecision.AVANZAR  # SELECT: funciona

    with pytest.raises(DBAPIError, match="permission denied"):
        await db_session.execute(
            text("UPDATE decisiones_candidato SET decision = 'DESCARTAR' WHERE id = :id"), {"id": decision_id}
        )
        await db_session.commit()
    await db_session.rollback()

    with pytest.raises(DBAPIError, match="permission denied"):
        await db_session.execute(text("DELETE FROM decisiones_candidato WHERE id = :id"), {"id": decision_id})
        await db_session.commit()
    await db_session.rollback()


async def _indicador_oe3(db: AsyncSession) -> tuple[dict[str, tuple[int, int]], int]:
    """Ejecuta la consulta documentada; retorna {etapa: (completaron, con_decision)} y las
    decisiones contrarias sin justificación."""
    sentencias = [s for s in CONSULTA_OE3.read_text(encoding="utf-8").split(";") if "SELECT" in s]
    assert len(sentencias) == 2
    cobertura = (await db.execute(text(sentencias[0]))).all()
    contrarias = (await db.execute(text(sentencias[1]))).scalar_one()
    return {fila.etapa: (fila.completaron, fila.con_decision) for fila in cobertura}, contrarias


async def _pasar_a(db: AsyncSession, candidato: Candidato, estado: EstadoCandidato) -> None:
    """Transición automática (la que haría el examen o la entrevista al terminar)."""
    db.add(candidato)
    candidato.estado = estado
    await db.commit()


async def test_el_proceso_completo_registra_el_100_por_ciento_de_las_decisiones(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]  # noqa: F811
) -> None:
    """Avances, descartes, decisiones contrarias, lote, reversión y contratación: OE3 = 100 %."""
    vacante = await _vacante(db_session)
    alto = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=85, sufijo="a")
    bajo = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=30, sufijo="b")
    rescatado = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=40, sufijo="c")
    lote_a = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=70, sufijo="d")
    lote_b = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=10, sufijo="e")
    pendiente = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=65, sufijo="f")

    def decidir(candidato: Candidato, etapa: str, decision: str, justificacion: str | None = None) -> None:
        respuesta = _decidir(
            client, admin_headers, candidato.id, etapa=etapa, decision=decision, justificacion_humana=justificacion
        )
        assert respuesta.status_code == 200, respuesta.text

    # Etapa CV
    decidir(alto, "cv", "avanzar")
    decidir(bajo, "cv", "descartar")
    decidir(bajo, "cv", "avanzar", "Revertido: experiencia relevante no detectada")  # reversión contraria
    decidir(rescatado, "cv", "avanzar", "Proyectos verificables en GitHub")
    lote = client.post(
        "/api/candidatos/decisiones/lote",
        json={
            "etapa": "cv",
            "decisiones": [
                {"candidato_id": lote_a.id, "decision": "avanzar"},
                {"candidato_id": lote_b.id, "decision": "descartar"},
            ],
        },
        headers=admin_headers,
    )
    assert lote.status_code == 200, lote.text

    # Etapa examen (la calificación deja examen_por_confirmar)
    for candidato, nota in ((alto, 17.0), (rescatado, 9.0)):
        await _examen(db_session, candidato, nota)
        await _pasar_a(db_session, candidato, EstadoCandidato.EXAMEN_POR_CONFIRMAR)
    decidir(alto, "examen", "avanzar")
    decidir(rescatado, "examen", "descartar")

    # Etapa entrevista (el análisis deja entrevista_realizada) y contratación manual
    await _pasar_a(db_session, alto, EstadoCandidato.ENTREVISTA_REALIZADA)
    decidir(alto, "entrevista", "avanzar")
    contratado = client.post(
        f"/api/candidatos/{alto.id}/cambiar-estado", json={"estado": "contratado"}, headers=admin_headers
    )
    assert contratado.status_code == 200

    cobertura, contrarias = await _indicador_oe3(db_session)

    assert cobertura == {"CV": (5, 5), "EXAMEN": (2, 2), "ENTREVISTA": (1, 1)}
    assert contrarias == 0
    assert pendiente.id  # sigue por confirmar: no completó la etapa y no cuenta en el denominador


async def test_la_consulta_detecta_un_estado_de_decision_sin_fila(db_session: AsyncSession) -> None:
    """Un candidato puesto en cv_aprobado sin pasar por el servicio rompe el 100 %."""
    vacante = await _vacante(db_session)
    await _candidato(db_session, vacante, EstadoCandidato.CV_APROBADO, sufijo="x")

    cobertura, _ = await _indicador_oe3(db_session)
    assert cobertura["CV"] == (1, 0)
