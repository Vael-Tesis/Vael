"""Catálogo de eventos de proctoring y cálculo del semáforo de riesgo (sección 11 del CLAUDE.md).

Compartido entre examen (puntaje_riesgo/semaforo en el propio modelo Examen) y entrevista
(que hoy solo registra el evento en EventoAuditoria, sin un acumulado propio en EntrevistaIA).
"""
from app.models.evaluacion import SemaforoExamen, SeveridadEvento

CATALOGO_EVENTOS_PROCTORING: dict[str, tuple[SeveridadEvento, int]] = {
    "perdida_foco": (SeveridadEvento.MEDIA, 3),
    "cambio_ventana": (SeveridadEvento.MEDIA, 4),
    "pantalla_dividida": (SeveridadEvento.MEDIA, 3),
    "inactividad": (SeveridadEvento.BAJA, 2),
    "copy_paste": (SeveridadEvento.ALTA, 6),
    "click_derecho": (SeveridadEvento.ALTA, 5),
    "devtools": (SeveridadEvento.ALTA, 8),
    "multiples_voces": (SeveridadEvento.ALTA, 10),
    "sin_rostro": (SeveridadEvento.ALTA, 8),
    "segunda_persona": (SeveridadEvento.ALTA, 10),
}
EVENTO_DEFAULT: tuple[SeveridadEvento, int] = (SeveridadEvento.BAJA, 1)


def calcular_semaforo(puntaje_riesgo: int) -> SemaforoExamen:
    """Traduce un puntaje de riesgo acumulado al semáforo correspondiente."""
    if puntaje_riesgo <= 6:
        return SemaforoExamen.VERDE
    if puntaje_riesgo <= 18:
        return SemaforoExamen.AMARILLO
    return SemaforoExamen.ROJO
