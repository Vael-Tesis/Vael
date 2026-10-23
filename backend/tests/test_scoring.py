"""Pruebas de la fórmula del score final (DEC-007, tarea DEV-C-01)."""
import pytest

from app.core.scoring import PESO_CV, PESO_ENTREVISTA, PESO_EXAMEN, calcular_score_final


def test_ejemplo_de_referencia_de_dec_007() -> None:
    """CV 78, examen 15 y entrevista 16.1 deben dar 15.56 (ejemplo del ADR)."""
    assert calcular_score_final(78, 15, 16.1) == 15.56


@pytest.mark.parametrize(
    ("score_cv", "nota_examen", "nota_entrevista"),
    [
        (None, 15, 16.1),
        (78, None, 16.1),
        (78, 15, None),
        (None, None, None),
    ],
)
def test_score_es_none_si_falta_alguna_nota(
    score_cv: float | None,
    nota_examen: float | None,
    nota_entrevista: float | None,
) -> None:
    """Sin las tres notas no hay score final: el candidato va aparte en el ranking."""
    assert calcular_score_final(score_cv, nota_examen, nota_entrevista) is None


def test_limite_superior_es_20() -> None:
    """Las tres notas al máximo dan exactamente 20.00."""
    assert calcular_score_final(100, 20, 20) == 20.00


def test_limite_inferior_es_0() -> None:
    """Las tres notas en cero dan 0.00, no None (cero es una nota válida)."""
    assert calcular_score_final(0, 0, 0) == 0.00


def test_redondeo_a_dos_decimales() -> None:
    """El resultado se redondea a 2 decimales."""
    resultado = calcular_score_final(91, 17.5, 18.2)
    assert resultado == 17.92
    assert resultado == round(resultado, 2)


def test_pesos_suman_uno() -> None:
    """Los pesos de DEC-007 suman 100%, así que el score queda en la escala 0-20."""
    assert PESO_CV + PESO_EXAMEN + PESO_ENTREVISTA == pytest.approx(1.0)
