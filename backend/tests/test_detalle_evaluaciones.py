"""RF-A-16 (HU-19): el detalle del examen y el de la entrevista muestran su contenido completo.

`test_registro_candidatos.py::test_la_bandeja_muestra_el_semaforo_del_examen` y
`test_auditoria_general.py` ya cubren el semáforo y la auditoría; falta el detalle en sí
(GET /evaluaciones/examenes/{id} con sus preguntas, y GET /entrevista/detalle/{id} con
transcripción, dimensiones y capturas), que ningún otro test ejercía."""
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.candidato import EstadoCandidato
from app.models.entrevista import CapturaAuditoria, EntrevistaIA, EstadoEntrevista, TipoCaptura
from app.models.evaluacion import EstadoExamen, Examen, PreguntaExamen, TipoPregunta
from tests.test_decisiones import _candidato, _vacante


async def test_detalle_de_examen_incluye_sus_preguntas_y_respuestas(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.EXAMEN_POR_CONFIRMAR, sufijo="examen-detalle")
    examen = Examen(
        tenant_id=candidato.tenant_id, candidato_id=candidato.id, vacante_id=vacante.id,
        estado=EstadoExamen.FINALIZADO, nota=15.0,
    )
    db_session.add(examen)
    await db_session.flush()
    pregunta = PreguntaExamen(
        tenant_id=candidato.tenant_id, examen_id=examen.id, orden=1, tipo=TipoPregunta.ABIERTA,
        enunciado="Explica qué es la inyección de dependencias", respuesta_candidato="Es un patrón de diseño...",
        puntos_max=2.0, puntos_obtenidos=1.5, feedback_ia="Respuesta correcta, le falta un ejemplo",
    )
    db_session.add(pregunta)
    await db_session.commit()

    respuesta = client.get(f"/api/evaluaciones/examenes/{examen.id}", headers=admin_headers)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["nota"] == 15.0
    assert len(cuerpo["preguntas"]) == 1
    fila = cuerpo["preguntas"][0]
    assert fila["enunciado"] == "Explica qué es la inyección de dependencias"
    assert fila["respuesta_candidato"] == "Es un patrón de diseño..."
    assert fila["puntos_obtenidos"] == 1.5
    assert fila["feedback_ia"] == "Respuesta correcta, le falta un ejemplo"


async def test_detalle_de_entrevista_incluye_transcripcion_dimensiones_y_capturas(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.ENTREVISTA_REALIZADA, sufijo="entrevista-detalle")
    entrevista = EntrevistaIA(
        tenant_id=candidato.tenant_id, candidato_id=candidato.id, vacante_id=vacante.id,
        estado=EstadoEntrevista.FINALIZADA, nota=17.0, transcripcion="Candidato: buenos días...",
        audio_url="https://s3.local/audio.mp3", duracion_minutos=22,
        dimensiones_json={"comunicacion": 18.0, "tecnico": 16.0},
    )
    db_session.add(entrevista)
    await db_session.flush()
    captura = CapturaAuditoria(
        tenant_id=candidato.tenant_id, entrevista_id=entrevista.id, tipo=TipoCaptura.IDENTIDAD,
        imagen_url="https://s3.local/captura.jpg",
    )
    db_session.add(captura)
    await db_session.commit()

    respuesta = client.get(f"/api/entrevista/detalle/{entrevista.id}", headers=admin_headers)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["candidato_nombre"] == candidato.nombre
    assert cuerpo["nota"] == 17.0
    assert cuerpo["transcripcion"] == "Candidato: buenos días..."
    assert cuerpo["dimensiones_json"] == {"comunicacion": 18.0, "tecnico": 16.0}
    assert len(cuerpo["capturas"]) == 1
    assert cuerpo["capturas"][0]["tipo"] == "identidad"
