# DEC-026 — Registros separados del OE2 para Gemini y Qwen

| Campo | Valor |
|---|---|
| Estado | Propuesta |
| Fecha | 2026-11-10 |
| Tarea de origen | TST-A-06 (medición del OE2 para la presentación del 2026-11-11) |
| Propuesto por | Gabriel Llanos (Product Owner); registrada por Gabriel Llanos |
| Relacionada con | DEC-025 (respaldo de IA), DEC-024 (desglose del score), OE2 (doc 14), TST-A-05 |

## Contexto

- **HECHO:** el OE2 (doc 14) mide la consistencia del análisis de CV: desviación estándar ≤ 5 puntos en 10 ejecuciones del mismo CV. Hasta hoy no hay ninguna corrida completa con Gemini:
  - 2026-11-03: falló por cuota y alta demanda (PR #35, `intento_01_cuota_agotada.json`);
  - 2026-11-09: se detuvo sin resultados por la cuota diaria.
- **HECHO del 2026-11-10:** de 09:09 a 09:16 (hora de Lima), 5 llamadas mínimas a `gemini-3.8-flash` respondieron 503 («high demand»). Ninguna respondió 429.
- **HECHO:** el plan gratuito de Gemini permite 20 solicitudes por día. El OE2 completo (30 llamadas) no cabe en un día. El prepago de Google Cloud exige un mínimo de PEN 100.
- **HECHO:** el equipo consiguió una API de Qwen compatible con la de OpenAI. Funciona con el cliente de DEC-025 (`core/qwen.py`) cambiando solo `QWEN_BASE_URL`, `QWEN_MODEL` y `QWEN_API_KEY`.
- **HECHO:** la presentación es el 2026-11-11.

## Decisión

1. **El OE2 tiene dos registros separados, uno por modelo:**
   - `docs/metricas/oe2_gemini/`: Gemini, el proveedor del sistema;
   - `docs/metricas/oe2_qwen/`: Qwen.

   Cada carpeta tiene su corrida completa (`consistencia.json`), sus intentos fallidos (`intento_NN_<motivo>.json`) y sus partes (`partes/`). **Ninguno reemplaza al otro.**
2. **El mismo procedimiento en ambos:** prompt, vacante, CV, validación del desglose (DEC-024) y regla de recomendación son los del sistema. Solo cambia el modelo.
3. **Se elige el proveedor de forma explícita:** `python -m app.scripts.medir_oe2 --proveedor gemini|qwen`. El argumento es obligatorio, para que una medición nunca quede en el registro equivocado.
4. **Cada ejecución registra el proveedor y el modelo,** y en Qwen también el servidor. Nunca se registra la clave.
5. **El intento fallido de Gemini del 2026-11-03 se conserva** en el registro de Gemini como intento, no como resultado. Antes estaba en `docs/metricas/oe2_intento_01_cuota_agotada.json`.
6. **Cómo se informa:**
   - en la presentación y en la monografía, cada cifra se presenta con su modelo («consistencia del análisis de CV con Qwen, medida el 2026-11-10»);
   - el resultado de Qwen no se presenta como medición de Gemini;
   - mientras Gemini no tenga una corrida completa, su registro se informa como pendiente.

## Consecuencias

- **Medición a tiempo:** se obtiene una medición real del pipeline de VAEL para la presentación, sin perder la de Gemini cuando esté disponible.
- **Comparación posible:** con los dos registros completos, se puede comparar la consistencia de ambos modelos con el mismo procedimiento.
- **Limitación que hay que declarar:** el resultado de Qwen describe a ese modelo; no demuestra la consistencia de Gemini.
- **Datos personales:** los CV de la medición son ficticios (doc 13), así que no se envían datos personales reales al proveedor de Qwen. Con datos reales habría que evaluar la transferencia de datos (Ley 29733).
- **Cambia el doc 14:** pasa a tener dos registros y cambian las rutas de los archivos. Su responsable lo actualiza.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Esperar a Gemini | 503 sostenido el día de la medición y tope de 20 llamadas diarias: no hay corrida completa antes de la presentación |
| Prepago de Gemini (PEN 100 mínimo) | Rechazado por el Product Owner por costo; además no garantiza evitar el 503 |
| Reemplazar el registro de Gemini por el de Qwen | Se pierde el registro del proveedor del sistema y la posibilidad de comparar; el Product Owner pidió conservar ambos |
| Forzar `IA_PROVEEDOR=qwen` en el script anterior | Quedaría registrado como `gemini-3.8-flash`: un registro falso |
