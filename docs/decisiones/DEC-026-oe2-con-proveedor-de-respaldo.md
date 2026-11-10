# DEC-026 — Medir el OE2 con el proveedor de respaldo ante la indisponibilidad de Gemini

| Campo | Valor |
|---|---|
| Estado | Propuesta |
| Fecha | 2026-11-10 |
| Tarea de origen | TST-A-06 (medición del OE2 para la presentación del 2026-11-11) |
| Propuesto por | Gabriel Llanos (Product Owner); registrada por Gabriel Llanos |
| Relacionada con | DEC-025 (respaldo de IA), DEC-024 (desglose del score), OE2 (doc 14), TST-A-05 |

## Contexto

- **HECHO:** el OE2 (doc 14) mide la consistencia del análisis de CV: desviación estándar ≤ 5 puntos en 10 ejecuciones del mismo CV. Hasta hoy no hay ninguna corrida exitosa:
  - 2026-11-03: falló por cuota y alta demanda (PR #35);
  - 2026-11-09: se detuvo sin resultados por la cuota diaria.
- **HECHO del 2026-11-10:** de 09:09 a 09:16 (hora de Lima), 5 llamadas mínimas a `gemini-3.8-flash` respondieron 503 («high demand»). Ninguna respondió 429.
- **HECHO:** el plan gratuito de Gemini permite 20 solicitudes por día. Aunque Gemini respondiera, el OE2 completo (30 llamadas) no cabe en un día. El prepago de Google Cloud exige un mínimo de PEN 100.
- **HECHO:** la presentación es el 2026-11-11, así que hoy es el último día para medir.
- **HECHO:** DEC-025 dejó un cliente compatible con la API de OpenAI (`core/qwen.py`). Ese cliente funciona con cualquier proveedor de esa API cambiando solo la configuración.

## Decisión

1. **El OE2 se mide hoy con un proveedor de respaldo de pago por uso (DeepSeek).** Se configura en `QWEN_BASE_URL`, `QWEN_MODEL` y `QWEN_API_KEY`, sin cambiar el prompt, la vacante, los CV, la validación del desglose (DEC-024) ni la regla de recomendación.
2. **El resultado declara el modelo real.** `medir_oe2 --proveedor respaldo`:
   - registra el proveedor, el modelo y el servidor en cada ejecución;
   - lo guarda en `docs/metricas/oe2_consistencia_respaldo.json`;
   - nunca usa `oe2_consistencia.json`, que queda reservado para la medición con Gemini.
3. **El OE2 con Gemini sigue pendiente,** no se da por cumplido. Si Gemini vuelve a estar disponible (o se paga el prepago), se mide con `medir_oe2` sin cambios y se informan ambos resultados.
4. **En la presentación y en la monografía,** la cifra se presenta como «consistencia del análisis de CV con DeepSeek (respaldo), medida el 2026-11-10». No se presenta como medición de Gemini.

## Consecuencias

- **Se obtiene una medición real** del pipeline de VAEL (prompt, validación y regla de decisión) a tiempo para la presentación.
- **El resultado describe otro modelo.** No demuestra la consistencia de Gemini. Es una limitación que hay que declarar.
- **Los CV de la medición son ficticios (doc 13).** No se envían datos personales reales a DeepSeek. Usar ese proveedor con datos reales exigiría evaluar la transferencia internacional de datos (Ley 29733).
- **Cambia el alcance del doc 14:** su responsable lo actualiza.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Esperar a Gemini | 503 sostenido el día de la medición y tope de 20 llamadas diarias: no hay corrida completa antes de la presentación |
| Prepago de Gemini (PEN 100 mínimo) | Rechazado por el Product Owner por costo; además no garantiza evitar el 503 |
| Forzar `IA_PROVEEDOR=qwen` en el script existente | Quedaría registrado como `gemini-3.8-flash`: un registro falso |
| Qwen de Tecsup | Solo alcanzable en el campus; la medición se hace hoy fuera de él |
