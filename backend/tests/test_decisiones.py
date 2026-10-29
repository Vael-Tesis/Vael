"""Pruebas de la supervisión humana (DEC-009) y del correo de cierre (DEC-013) — DEV-C-10.

Cubren las secciones "Validación" de ambos ADRs: la IA deja al candidato por confirmar sin
token ni correo; solo la decisión humana avanza o descarta; la decisión contraria exige
justificación; el lote solo acepta coincidencias; cambiar-estado no asigna estados de
decisión; y el correo de cierre es único y no revela puntajes ni razones.
"""
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import create_access_token
from app.models.area import Area
from app.models.candidato import Candidato, EstadoCandidato
from app.models.decision import DecisionCandidato
from app.models.evaluacion import EstadoExamen, Examen, PreguntaExamen, TipoPregunta
from app.models.usuario import Empresa, RolUsuario, TokenAcceso, Usuario
from app.models.vacante import EstadoVacante, Vacante
from app.services import analisis_cv, correos, examen
from tests.conftest import TENANT_ID

RESUMEN_IA = "Resumen generado por la IA con razones internas"


@pytest.fixture
def enviados(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Reemplaza el envío real de correos por un registro en memoria."""
    registro: list[dict[str, str]] = []

    async def enviar_falso(destinatario: str, asunto: str, html: str) -> None:
        registro.append({"para": destinatario, "asunto": asunto, "html": html})

    monkeypatch.setattr(correos, "_enviar_correo", enviar_falso)
    return registro


async def _vacante(db: AsyncSession) -> Vacante:
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    db.add(area)
    await db.flush()
    vacante = Vacante(
        tenant_id=TENANT_ID,
        area_id=area.id,
        codigo="TI-2026-001",
        titulo="Desarrollador Backend Python",
        estado=EstadoVacante.ABIERTA,
        score_cv_minimo=60,
        nota_minima_examen=13,
    )
    db.add(vacante)
    db.add(Empresa(tenant_id=TENANT_ID, nombre="Andina Servicios S.A.C.", email_contacto="datos@andina.example.com"))
    await db.commit()
    return vacante


async def _candidato(
    db: AsyncSession, vacante: Vacante, estado: EstadoCandidato, score_cv: int | None = 80, sufijo: str = "1"
) -> Candidato:
    candidato = Candidato(
        tenant_id=TENANT_ID,
        vacante_id=vacante.id,
        nombre="Lucía",
        apellidos=f"Quispe {sufijo}",
        email=f"lucia{sufijo}@example.com",
        estado=estado,
        score_cv=score_cv,
        resumen_ia=RESUMEN_IA,
    )
    db.add(candidato)
    await db.commit()
    return candidato


async def _examen(db: AsyncSession, candidato: Candidato, nota: float | None) -> Examen:
    registro = Examen(
        tenant_id=TENANT_ID,
        candidato_id=candidato.id,
        vacante_id=candidato.vacante_id,
        estado=EstadoExamen.FINALIZADO,
        nota=nota,
    )
    db.add(registro)
    await db.commit()
    return registro


async def _recargar(db: AsyncSession, candidato_id: str) -> Candidato:
    statement = select(Candidato).where(Candidato.id == candidato_id).execution_options(populate_existing=True)
    return (await db.exec(statement)).one()


async def _estado(db: AsyncSession, candidato_id: str) -> EstadoCandidato:
    return (await _recargar(db, candidato_id)).estado


async def _decisiones(db: AsyncSession, candidato_id: str) -> list[DecisionCandidato]:
    statement = select(DecisionCandidato).where(DecisionCandidato.candidato_id == candidato_id)
    return list((await db.exec(statement.order_by(DecisionCandidato.decidido_en))).all())


async def _tokens(db: AsyncSession, candidato_id: str) -> list[TokenAcceso]:
    statement = select(TokenAcceso).where(TokenAcceso.candidato_id == candidato_id)
    return list((await db.exec(statement.execution_options(populate_existing=True))).all())


def _decidir(client: TestClient, headers: dict[str, str], candidato_id: str, **body: Any) -> Any:
    return client.post(f"/api/candidatos/{candidato_id}/decision", json=body, headers=headers)


# --- La IA recomienda; no decide ---------------------------------------------------------


async def test_el_analisis_de_cv_deja_por_confirmar_sin_token_ni_correo(
    db_session: AsyncSession, enviados: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un score alto ya no aprueba: el candidato queda en cv_por_confirmar (DEC-009)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_ANALIZANDO, score_cv=None)
    candidato.cv_url = "https://s3.example.com/cv.pdf"

    async def pdf_falso(_url: str) -> bytes:
        return b"%PDF"

    async def gemini_falso(_prompt: str, model_name: str | None = None) -> dict[str, Any]:
        return {"score": 95, "clasificacion": "altamente_recomendado", "resumen": "Encaja muy bien"}

    monkeypatch.setattr(analisis_cv, "_descargar_pdf", pdf_falso)
    monkeypatch.setattr(analisis_cv, "extraer_texto_pdf", lambda _b: "Python FastAPI")
    monkeypatch.setattr(analisis_cv, "consultar_gemini_json", gemini_falso)

    await analisis_cv.analizar_cv(candidato, vacante, None, db_session)

    assert await _estado(db_session, candidato.id) is EstadoCandidato.CV_POR_CONFIRMAR
    assert await _tokens(db_session, candidato.id) == []
    assert enviados == []


async def test_la_calificacion_del_examen_deja_por_confirmar_sin_token_ni_correo(
    db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Aprobar el examen ya no invita a la entrevista: queda en examen_por_confirmar (DEC-009)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_RENDIDO)
    registro = await _examen(db_session, candidato, None)
    db_session.add_all(
        PreguntaExamen(
            tenant_id=TENANT_ID,
            examen_id=registro.id,
            orden=i,
            tipo=TipoPregunta.MULTIPLE_CHOICE,
            enunciado=f"Pregunta {i}",
            respuesta_correcta="a",
            respuesta_candidato="a",
            puntos_max=2.0,
        )
        for i in range(1, 11)
    )
    await db_session.commit()

    calificado = await examen.calificar_examen(registro.id, db_session)

    assert calificado.nota == 20
    assert await _estado(db_session, candidato.id) is EstadoCandidato.EXAMEN_POR_CONFIRMAR
    assert await _tokens(db_session, candidato.id) == []
    assert enviados == []


# --- Decisión individual -----------------------------------------------------------------


async def test_confirmar_avance_de_cv_emite_token_y_envia_correo(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Avanzar en CV: cv_aprobado, token de examen y correo de bienvenida; queda la fila."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=80)

    respuesta = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="avanzar")

    assert respuesta.status_code == 200, respuesta.text
    fila = respuesta.json()
    assert fila["recomendacion_ia"] == "avanzar"
    assert fila["coincide_con_ia"] is True
    assert fila["puntaje"] == 80 and fila["umbral"] == 60
    assert fila["justificacion_ia"] == RESUMEN_IA
    assert await _estado(db_session, candidato.id) is EstadoCandidato.CV_APROBADO
    assert [t.tipo.value for t in await _tokens(db_session, candidato.id)] == ["examen"]
    assert len(enviados) == 1 and "evaluación técnica" in enviados[0]["asunto"]


async def test_confirmar_descarte_envia_un_unico_correo_de_cierre_sin_puntajes(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Descartar: cv_rechazado y un correo de cierre sin puntaje ni justificación (DEC-013)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=35)

    respuesta = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="descartar")

    assert respuesta.status_code == 200, respuesta.text
    assert await _estado(db_session, candidato.id) is EstadoCandidato.CV_RECHAZADO
    assert await _tokens(db_session, candidato.id) == []
    assert len(enviados) == 1
    html = enviados[0]["html"]
    assert "Desarrollador Backend Python" in html
    assert "inteligencia artificial" in html and "revisada y confirmada" in html
    assert "datos@andina.example.com" in html
    texto = re.sub(r"<[^>]+>", " ", html)  # solo el texto visible, sin los estilos de la plantilla
    for prohibido in ("35", "60", RESUMEN_IA, "puntaje", "score", "nota"):
        assert prohibido not in texto.lower()


async def test_confirmar_dos_veces_el_mismo_descarte_no_duplica_nada(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Repetir la decisión vigente es idempotente: ni otra fila ni otro correo (DEC-013)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=35)

    primera = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="descartar")
    segunda = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="descartar")

    assert segunda.status_code == 200
    assert segunda.json()["id"] == primera.json()["id"]
    assert len(await _decisiones(db_session, candidato.id)) == 1
    assert len(enviados) == 1


async def test_decision_contraria_sin_justificacion_responde_422(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Ir contra la IA exige justificacion_humana; con ella, queda coincide_con_ia = false."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=40)

    sin = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="avanzar")
    vacia = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="avanzar", justificacion_humana="  ")
    assert sin.status_code == 422 and vacia.status_code == 422
    assert await _decisiones(db_session, candidato.id) == []
    assert await _estado(db_session, candidato.id) is EstadoCandidato.CV_POR_CONFIRMAR

    con = _decidir(
        client,
        admin_headers,
        candidato.id,
        etapa="cv",
        decision="avanzar",
        justificacion_humana="Tiene proyectos verificables que el CV no detalla",
        revision_inicio="2026-10-20T15:02:11",
    )
    assert con.status_code == 200, con.text
    assert con.json()["coincide_con_ia"] is False
    assert con.json()["revision_inicio"] == "2026-10-20T15:02:11"
    assert await _estado(db_session, candidato.id) is EstadoCandidato.CV_APROBADO


async def test_revertir_un_descarte_crea_fila_nueva_y_no_reenvia_el_cierre(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Revertir = fila nueva con reemplaza_a. Un segundo descarte no envía otro cierre."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=80)

    descarte = _decidir(
        client, admin_headers, candidato.id, etapa="cv", decision="descartar", justificacion_humana="Pretensión fuera de rango"
    ).json()
    avance = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="avanzar").json()
    otro_descarte = _decidir(
        client, admin_headers, candidato.id, etapa="cv", decision="descartar", justificacion_humana="Se confirmó el rango"
    )

    assert avance["reemplaza_a"] == descarte["id"]
    assert otro_descarte.json()["reemplaza_a"] == avance["id"]
    assert len(await _decisiones(db_session, candidato.id)) == 3
    assert await _estado(db_session, candidato.id) is EstadoCandidato.CV_RECHAZADO
    # Cierre, bienvenida al examen y nada más: el cierre es único por candidato y vacante
    asuntos = [c["asunto"] for c in enviados]
    assert len(asuntos) == 2 and "Actualización de tu postulación" in asuntos[0]
    # El token que emitió el avance ya no sirve
    assert all(t.usado for t in await _tokens(db_session, candidato.id))


async def test_no_se_decide_una_etapa_que_no_esta_pendiente(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Sin recomendación pendiente en esa etapa, la decisión responde 409."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_ANALIZANDO)

    assert _decidir(client, admin_headers, candidato.id, etapa="cv", decision="avanzar").status_code == 409
    assert _decidir(client, admin_headers, candidato.id, etapa="examen", decision="avanzar").status_code == 409
    assert _decidir(client, admin_headers, "no-existe", etapa="cv", decision="avanzar").status_code == 404


async def test_examen_avanzar_invita_a_la_entrevista(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Avanzar en examen: examen_aprobado, token de entrevista e invitación."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_POR_CONFIRMAR)
    await _examen(db_session, candidato, 15.0)

    respuesta = _decidir(client, admin_headers, candidato.id, etapa="examen", decision="avanzar")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["puntaje"] == 15.0 and respuesta.json()["umbral"] == 13
    assert await _estado(db_session, candidato.id) is EstadoCandidato.EXAMEN_APROBADO
    assert [t.tipo.value for t in await _tokens(db_session, candidato.id)] == ["entrevista"]
    assert len(enviados) == 1


async def test_entrevista_avanzar_marca_finalista_y_descartar_cierra(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """En la entrevista no hay recomendación: la decisión no exige justificación."""
    vacante = await _vacante(db_session)
    finalista = await _candidato(db_session, vacante, EstadoCandidato.ENTREVISTA_REALIZADA, sufijo="a")
    descartado = await _candidato(db_session, vacante, EstadoCandidato.ENTREVISTA_REALIZADA, sufijo="b")

    a = _decidir(client, admin_headers, finalista.id, etapa="entrevista", decision="avanzar")
    b = _decidir(client, admin_headers, descartado.id, etapa="entrevista", decision="descartar")

    assert a.status_code == 200 and a.json()["recomendacion_ia"] is None and a.json()["coincide_con_ia"] is None
    assert b.status_code == 200
    marcado = await _recargar(db_session, finalista.id)
    assert marcado.estado is EstadoCandidato.FINALISTA and marcado.es_finalista is True
    assert await _estado(db_session, descartado.id) is EstadoCandidato.DESCARTADO
    assert sorted(c["asunto"].split(" ")[0] for c in enviados) == ["Actualización", "Eres"]


# --- Lote ----------------------------------------------------------------------------------


async def test_el_lote_rechaza_decisiones_que_no_coinciden_y_no_ejecuta_ninguna(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Si una decisión del lote va contra la IA, responde 422 y no se registra ninguna."""
    vacante = await _vacante(db_session)
    alto = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=90, sufijo="a")
    bajo = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=20, sufijo="b")

    respuesta = client.post(
        "/api/candidatos/decisiones/lote",
        json={
            "etapa": "cv",
            "decisiones": [
                {"candidato_id": alto.id, "decision": "avanzar"},
                {"candidato_id": bajo.id, "decision": "avanzar"},
            ],
        },
        headers=admin_headers,
    )

    assert respuesta.status_code == 422
    assert await _decisiones(db_session, alto.id) == [] and await _decisiones(db_session, bajo.id) == []
    assert await _estado(db_session, alto.id) is EstadoCandidato.CV_POR_CONFIRMAR
    assert enviados == []


async def test_el_lote_confirma_las_decisiones_que_coinciden(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Un lote de coincidencias ejecuta cada efecto: avance con correo y descarte con cierre."""
    vacante = await _vacante(db_session)
    alto = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=90, sufijo="a")
    bajo = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=20, sufijo="b")

    respuesta = client.post(
        "/api/candidatos/decisiones/lote",
        json={
            "etapa": "cv",
            "decisiones": [
                {"candidato_id": alto.id, "decision": "avanzar"},
                {"candidato_id": bajo.id, "decision": "descartar"},
            ],
        },
        headers=admin_headers,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert all(d["coincide_con_ia"] for d in respuesta.json())
    assert await _estado(db_session, alto.id) is EstadoCandidato.CV_APROBADO
    assert await _estado(db_session, bajo.id) is EstadoCandidato.CV_RECHAZADO
    assert len(enviados) == 2


async def test_el_lote_no_acepta_la_etapa_de_entrevista_sin_recomendacion(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Sin recomendación no hay coincidencia posible: la entrevista se decide de forma individual."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.ENTREVISTA_REALIZADA)

    respuesta = client.post(
        "/api/candidatos/decisiones/lote",
        json={"etapa": "entrevista", "decisiones": [{"candidato_id": candidato.id, "decision": "avanzar"}]},
        headers=admin_headers,
    )
    assert respuesta.status_code == 422


# --- DEC-022: recomendación de finalistas con top_candidatos_finalistas -------------------


async def _finalista(
    db_session: AsyncSession, vacante: Vacante, score_final: float | None, sufijo: str
) -> Candidato:
    """Candidato que ya rindió la entrevista, con el score_final que ordena el ranking."""
    candidato = await _candidato(db_session, vacante, EstadoCandidato.ENTREVISTA_REALIZADA, sufijo=sufijo)
    candidato.score_final = score_final
    db_session.add(candidato)
    await db_session.commit()
    await db_session.refresh(candidato)
    return candidato


async def test_dec022_el_lote_avanza_a_los_primeros_del_ranking_y_descarta_al_resto(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Con top_candidatos_finalistas = 3 y cinco candidatos completos, los tres de mayor
    score_final avanzan y los otros dos se descartan (DEC-022, validación 1)."""
    vacante = await _vacante(db_session)
    vacante.top_candidatos_finalistas = 3
    db_session.add(vacante)
    await db_session.commit()
    candidatos = [await _finalista(db_session, vacante, score, str(i)) for i, score in enumerate([20, 18, 16, 14, 12])]

    respuesta = client.post(
        "/api/candidatos/decisiones/lote",
        json={
            "etapa": "entrevista",
            "decisiones": [
                {"candidato_id": c.id, "decision": "avanzar" if i < 3 else "descartar"} for i, c in enumerate(candidatos)
            ],
        },
        headers=admin_headers,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert all(fila["coincide_con_ia"] for fila in respuesta.json())
    assert await _estado(db_session, candidatos[0].id) is EstadoCandidato.FINALISTA
    assert await _estado(db_session, candidatos[2].id) is EstadoCandidato.FINALISTA
    assert await _estado(db_session, candidatos[3].id) is EstadoCandidato.DESCARTADO
    assert await _estado(db_session, candidatos[4].id) is EstadoCandidato.DESCARTADO


async def test_dec022_el_empate_en_el_ultimo_puesto_avanza_a_todos_los_empatados(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Un empate en el tercer puesto da avanzar a todos los empatados (DEC-022, validación 2)."""
    vacante = await _vacante(db_session)
    vacante.top_candidatos_finalistas = 3
    db_session.add(vacante)
    await db_session.commit()
    primero = await _finalista(db_session, vacante, 20, "a")
    empatado_1 = await _finalista(db_session, vacante, 15, "b")
    empatado_2 = await _finalista(db_session, vacante, 15, "c")
    ultimo = await _finalista(db_session, vacante, 10, "d")

    respuesta = client.post(
        "/api/candidatos/decisiones/lote",
        json={
            "etapa": "entrevista",
            "decisiones": [
                {"candidato_id": primero.id, "decision": "avanzar"},
                {"candidato_id": empatado_1.id, "decision": "avanzar"},
                {"candidato_id": empatado_2.id, "decision": "avanzar"},
                {"candidato_id": ultimo.id, "decision": "descartar"},
            ],
        },
        headers=admin_headers,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert await _estado(db_session, empatado_1.id) is EstadoCandidato.FINALISTA
    assert await _estado(db_session, empatado_2.id) is EstadoCandidato.FINALISTA
    assert await _estado(db_session, ultimo.id) is EstadoCandidato.DESCARTADO


async def test_dec022_sin_score_final_no_hay_recomendacion_ni_entra_en_el_lote(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """Un proceso incompleto (score_final nulo) no recibe recomendación: se decide individual,
    sin justificación, pero el lote lo rechaza (DEC-022, validación 3)."""
    vacante = await _vacante(db_session)
    incompleto = await _finalista(db_session, vacante, None, "a")

    individual = _decidir(client, admin_headers, incompleto.id, etapa="entrevista", decision="avanzar")
    assert individual.status_code == 200, individual.text
    assert individual.json()["recomendacion_ia"] is None

    otro = await _finalista(db_session, vacante, None, "b")
    en_lote = client.post(
        "/api/candidatos/decisiones/lote",
        json={"etapa": "entrevista", "decisiones": [{"candidato_id": otro.id, "decision": "avanzar"}]},
        headers=admin_headers,
    )
    assert en_lote.status_code == 422
    assert await _decisiones(db_session, otro.id) == []


async def test_dec022_el_lote_rechaza_una_decision_que_no_coincide_con_el_ranking(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """El lote rechaza una decisión que no coincide con la recomendación (DEC-022, validación 4):
    descartar a quien el ranking ubica entre los finalistas."""
    vacante = await _vacante(db_session)
    vacante.top_candidatos_finalistas = 1
    db_session.add(vacante)
    await db_session.commit()
    primero = await _finalista(db_session, vacante, 20, "a")
    segundo = await _finalista(db_session, vacante, 15, "b")

    respuesta = client.post(
        "/api/candidatos/decisiones/lote",
        json={
            "etapa": "entrevista",
            "decisiones": [
                {"candidato_id": primero.id, "decision": "descartar"},
                {"candidato_id": segundo.id, "decision": "descartar"},
            ],
        },
        headers=admin_headers,
    )

    assert respuesta.status_code == 422
    assert await _decisiones(db_session, primero.id) == []
    assert await _decisiones(db_session, segundo.id) == []


# --- cambiar-estado, correos, bandeja e historial -----------------------------------------


@pytest.mark.parametrize(
    "estado", ["cv_aprobado", "cv_rechazado", "examen_aprobado", "examen_rechazado", "finalista", "descartado"]
)
async def test_cambiar_estado_rechaza_los_estados_de_decision_humana(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, estado: str
) -> None:
    """Los avances y descartes solo pasan por el endpoint de decisiones (DEC-009, punto 5)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR)

    respuesta = client.post(
        f"/api/candidatos/{candidato.id}/cambiar-estado", json={"estado": estado}, headers=admin_headers
    )
    assert respuesta.status_code == 422
    assert await _estado(db_session, candidato.id) is EstadoCandidato.CV_POR_CONFIRMAR


async def test_cambiar_estado_sigue_aceptando_estados_automaticos(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """Un estado que no es de decisión se puede asignar a mano."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.FINALISTA)

    respuesta = client.post(
        f"/api/candidatos/{candidato.id}/cambiar-estado", json={"estado": "contratado"}, headers=admin_headers
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "contratado"


async def test_marcar_finalista_ya_no_existe(client: TestClient, admin_headers: dict[str, str]) -> None:
    """La ruta se reemplazó por la decisión de la etapa entrevista."""
    assert client.post("/api/candidatos/x/marcar-finalista", headers=admin_headers).status_code in (404, 405)


async def test_un_descartado_no_recibe_correos_de_avance(db_session: AsyncSession, enviados: list[Any]) -> None:
    """La guarda de correos bloquea los de avance a un descartado y el cierre a quien sigue en proceso."""
    vacante = await _vacante(db_session)
    descartado = await _candidato(db_session, vacante, EstadoCandidato.DESCARTADO, sufijo="a")
    en_proceso = await _candidato(db_session, vacante, EstadoCandidato.CV_APROBADO, sufijo="b")

    await correos.correo_bienvenida_examen(descartado, "token", vacante)
    await correos.correo_invitacion_entrevista(descartado, "token", vacante)
    await correos.correo_finalista(descartado, vacante)
    assert await correos.correo_cierre_proceso(en_proceso, vacante, None) is False
    assert enviados == []


async def test_reenviar_correo_a_un_descartado_solo_envia_el_cierre(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """reenviar-correo-etapa con un descartado envía el correo de cierre (DEC-013)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_RECHAZADO)

    respuesta = client.post(f"/api/candidatos/{candidato.id}/reenviar-correo-etapa", headers=admin_headers)
    assert respuesta.status_code == 200
    assert len(enviados) == 1 and "Actualización de tu postulación" in enviados[0]["asunto"]


async def test_bandeja_lista_las_recomendaciones_pendientes(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """La bandeja muestra CV y examen por confirmar con su recomendación; filtra por etapa."""
    vacante = await _vacante(db_session)
    cv = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=30, sufijo="a")
    ex = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_POR_CONFIRMAR, sufijo="b")
    await _examen(db_session, ex, 16.0)
    await _candidato(db_session, vacante, EstadoCandidato.CV_APROBADO, sufijo="c")

    todos = client.get("/api/candidatos/por-confirmar", params={"vacante_id": vacante.id}, headers=admin_headers)
    assert todos.status_code == 200, todos.text
    por_id = {item["candidato"]["id"]: item for item in todos.json()}
    assert set(por_id) == {cv.id, ex.id}
    assert por_id[cv.id]["etapa"] == "cv" and por_id[cv.id]["recomendacion_ia"] == "descartar"
    assert por_id[ex.id]["etapa"] == "examen" and por_id[ex.id]["recomendacion_ia"] == "avanzar"
    assert por_id[ex.id]["puntaje"] == 16.0

    solo_examen = client.get("/api/candidatos/por-confirmar", params={"etapa": "examen"}, headers=admin_headers)
    assert [item["candidato"]["id"] for item in solo_examen.json()] == [ex.id]


async def test_el_evaluador_no_decide_ni_ve_la_bandeja(client: TestClient, db_session: AsyncSession) -> None:
    """Deciden reclutador, admin y gerente; el evaluador solo consulta (DEC-009, punto 6)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR)
    evaluador = Usuario(
        tenant_id=TENANT_ID, nombre="Eva", apellidos="Luadora", email="evaluador@test.vael",
        password_hash="x", rol=RolUsuario.EVALUADOR,
    )
    db_session.add(evaluador)
    await db_session.commit()
    token = await create_access_token(evaluador.id, TENANT_ID, evaluador.rol.value)
    headers = {"Authorization": f"Bearer {token}"}

    assert _decidir(client, headers, candidato.id, etapa="cv", decision="avanzar").status_code == 403
    assert client.get("/api/candidatos/por-confirmar", headers=headers).status_code == 403
    assert client.get(f"/api/candidatos/{candidato.id}/decisiones", headers=headers).status_code == 200


async def test_historial_y_detalle_muestran_las_decisiones(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """El historial y el detalle del candidato incluyen cada decisión con su autor (HU-16)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=80)
    decision = _decidir(client, admin_headers, candidato.id, etapa="cv", decision="avanzar").json()

    historial = client.get(f"/api/candidatos/{candidato.id}/decisiones", headers=admin_headers)
    detalle = client.get(f"/api/candidatos/{candidato.id}", headers=admin_headers)

    assert [d["id"] for d in historial.json()] == [decision["id"]]
    assert historial.json()[0]["decidido_por"] == decision["decidido_por"]
    assert historial.json()[0]["decidido_por_nombre"] == "Test admin"
    assert [d["id"] for d in detalle.json()["decisiones"]] == [decision["id"]]


async def test_revision_inicio_con_zona_horaria_se_guarda_en_utc(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """El navegador envía la fecha con zona (ISO con Z u offset); se guarda en UTC sin zona."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_POR_CONFIRMAR, score_cv=80)

    respuesta = _decidir(
        client, admin_headers, candidato.id, etapa="cv", decision="avanzar", revision_inicio="2026-10-20T10:02:11-05:00"
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["revision_inicio"] == "2026-10-20T15:02:11"


async def test_reenviar_tras_aprobar_el_examen_reenvia_la_invitacion(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, enviados: list[Any]
) -> None:
    """examen_aprobado es el estado que deja confirmar el examen: se puede reenviar la invitación."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_APROBADO)

    respuesta = client.post(f"/api/candidatos/{candidato.id}/reenviar-correo-etapa", headers=admin_headers)

    assert respuesta.status_code == 200
    assert len(enviados) == 1 and "siguiente paso" in enviados[0]["asunto"]
