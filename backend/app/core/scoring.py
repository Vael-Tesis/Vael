"""Cálculo del score final del candidato (DEC-007).

score_final = (score_cv / 5) × 0.20 + nota_examen × 0.40 + nota_entrevista × 0.40

Las tres notas quedan en escala 0-20 y el resultado se redondea a 2 decimales. Si falta
alguna nota, el score es None: el candidato aparece en el ranking como "proceso incompleto".
El score es una recomendación para ordenar el ranking, no una decisión (DEC-009).
"""

# El CV se califica sobre 100; dividir entre 5 lo lleva a la escala 0-20 de las otras notas.
FACTOR_CV_A_ESCALA_20 = 5
PESO_CV = 0.20
PESO_EXAMEN = 0.40
PESO_ENTREVISTA = 0.40


def calcular_score_final(
    score_cv: float | None,
    nota_examen: float | None,
    nota_entrevista: float | None,
) -> float | None:
    """Devuelve el score final en escala 0-20, o None si falta alguna de las tres notas."""
    if score_cv is None or nota_examen is None or nota_entrevista is None:
        return None
    cv_en_escala_20 = score_cv / FACTOR_CV_A_ESCALA_20
    return round(
        cv_en_escala_20 * PESO_CV + nota_examen * PESO_EXAMEN + nota_entrevista * PESO_ENTREVISTA,
        2,
    )
