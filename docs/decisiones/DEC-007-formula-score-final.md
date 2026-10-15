# DEC-007 — Fórmula del score final

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-02 (decisión 1) — roadmap `11_roadmap_post_E2.md` v1.1 |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Reemplaza | Pesos 25/40/35 del doc 07, etapa 19 (sin justificación documentada) |
| Relacionada con | DEC-003 (supervisión humana) |

## Contexto

El doc 07 (etapa 19) define `score_final = score_cv × 0.25 + nota_examen × 0.40 + nota_entrevista × 0.35` e indica que `score_cv` (0-100) se divide entre 5 para quedar en escala 0-20.

La auditoría del código (2026-10-05) encontró que esa normalización no está implementada. Con el ejemplo del doc 07 (CV 78, examen 15, entrevista 16.1), el código produce 31.14, un valor fuera de la escala 0-20, y los pesos efectivos quedan en 62.5/20/17.5. La fórmula documentada, normalizada, produce 15.54.

Además, los pesos 25/40/35 no tienen justificación en ningún documento del proyecto, y el doc 10 (sección 2.5) exige justificarlos ante el tribunal.

Evidencia disponible: Sackett et al. (2022), ya citado en el Capítulo I, reporta validez operativa media de .42 para la entrevista estructurada (intervalo de credibilidad al 80%: .18 a .66), .40 para las pruebas de conocimiento del puesto y .07 para los años de experiencia. El score de CV, además, ya cumple la función de filtro de entrada (umbral por defecto 60/100).

## Decisión

1. **Normalización:** `score_cv / 5`, de modo que las tres notas queden en escala 0-20.
2. **Fórmula:**

   ```
   score_final = (score_cv / 5) × 0.20 + nota_examen × 0.40 + nota_entrevista × 0.40
   ```

   Resultado redondeado a 2 decimales. Los pesos se definen como constantes con nombre en el código, no como literales dispersos.
3. **Dominio:** `score_final` solo se calcula cuando existen las tres notas. Si falta alguna, queda en `null` y el ranking muestra al candidato aparte como "proceso incompleto".
4. **Naturaleza:** `score_final` es una recomendación para ordenar el ranking, no una decisión. Las decisiones de avance o descarte requieren confirmación humana (DEC-003).

Ejemplo de referencia (CV 78, examen 15, entrevista 16.1):
15.6 × 0.20 + 15 × 0.40 + 16.1 × 0.40 = 3.12 + 6.00 + 6.44 = **15.56**

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| A. Mantener 25/40/35 (doc 07) | Pesos sin justificación; además ordenan el examen por encima de la entrevista, en sentido contrario a la evidencia disponible |
| C. Pesos proporcionales exactos a la validez (≈8/45/47) | Precisión falsa: EVA y el examen generado por IA no son los instrumentos medidos por Sackett et al. (2022) |
| D. Pesos configurables por vacante | Requiere modelo, interfaz, validación y tests adicionales; amplía el alcance sin aportar a los objetivos específicos |
| Excluir el CV del score final (0/50/50) | Contradice el alcance entregado en el Capítulo I ("puntaje final ponderado a partir de las tres etapas") |

## Trade-off aceptado

Los pesos están **informados** por la literatura, pero **no validados** para VAEL. Las validez reportadas corresponden a instrumentos aplicados por personas; que el mismo orden se mantenga cuando los aplica una IA es una **hipótesis**, coherente con la limitación declarada en la sección 1.3 de la monografía ("consistencia no equivale a acierto"). Su validación queda como trabajo futuro.

## Consecuencias

Documentos a actualizar:
- Doc 07, etapa 19: fórmula y ejemplo numérico.
- Doc 10, sección 2.5: pesos, justificación y ejemplo numérico.
- Roadmap, DEV-C-01: el CA pasa a ser un test unitario con el ejemplo de este ADR (resultado esperado 15.56) y un test de `null` cuando falta alguna nota.
- Monografía, Capítulo III: presentar esta decisión con sus alternativas descartadas.

Implementación: tarea DEV-C-01.

## Validación

- Test unitario: CV 78, examen 15, entrevista 16.1 → 15.56.
- Test unitario: cualquier nota ausente → `score_final` = `null`.
- Test de límites: (100, 20, 20) → 20.00 y (0, 0, 0) → 0.00.

## Referencias

Sackett, P. R., Zhang, C., Berry, C. M., & Lievens, F. (2022). Revisiting meta-analytic estimates of validity in personnel selection: Addressing systematic overcorrection for restriction of range. *Journal of Applied Psychology, 107*(11), 2040–2068.
