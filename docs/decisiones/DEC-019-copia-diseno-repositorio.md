# DEC-019 — Copia de los documentos de diseño en el repositorio

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-18 |
| Tarea de origen | PLN-C-03 (coherencia de la documentación) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Relacionada con | DEC-017 (metodología), `CLAUDE.md` v2.1 |

## Contexto

- `CLAUDE.md` v2.1 es compacto y remite a los documentos del Drive (docs 05, 06, 07, 08 y 13 a 16) para el detalle del modelo de datos, la API, el flujo, los servicios, los datos semilla, las métricas, las vistas y los requerimientos.
- Claude Code trabaja dentro del repositorio y **no tiene acceso al Drive**. Sin esos documentos, el agente solo cuenta con el código y el OpenAPI, que no describen lo planificado (estados nuevos, tabla de decisiones, endpoints pendientes).
- El Drive es la fuente de verdad de la documentación de diseño (roadmap, PLN-C-03).

## Decisión

1. Se crea la carpeta `docs/diseno/` en el repositorio con **copias** de los documentos de diseño que necesita el desarrollo: 05, 06, 07, 08, 13, 14, 15 y 16.
2. Cada copia empieza con un encabezado:

   ```
   > COPIA del documento del Drive `VAEL/Docs/<nombre>`, versión <X>, copiada el <fecha>.
   > La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.
   ```

3. Las copias se generan con el script `scripts/sincronizar-diseno.ps1`, que toma los archivos descargados del Drive, lee su versión y agrega el encabezado. Se actualizan en el mismo PR (*Pull Request*) en que cambia el documento del Drive, o en el pase de documentación del sprint, con un commit `docs(<ID>): sincronizar docs/diseno con el Drive`.
4. `CLAUDE.md` remite a `docs/diseno/` en lugar de "doc NN del Drive".
5. Los documentos que no se copian (00 a 04, 09 a 12, la monografía) siguen solo en el Drive: son de contexto, infraestructura o redacción académica, no instrucciones de desarrollo.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Adjuntar el documento en cada prompt de Claude Code | Depende de que nadie lo olvide; el agente puede trabajar sin el contexto sin advertirlo |
| Mover toda la documentación al repositorio | Rompe el flujo del equipo con el Drive y con la monografía |

## Trade-off aceptado

El mismo texto existe en dos lugares. Se mitiga con el encabezado de versión, la regla de que el Drive manda y la prohibición de editar las copias.

## Consecuencias

- `CLAUDE.md`: las referencias a "doc NN" pasan a `docs/diseno/NN_*.md`.
- Roadmap: la *Definition of Done* incluye sincronizar `docs/diseno/` cuando cambia un documento de diseño.
- La primera copia se hizo el 2026-10-18, tras actualizar los docs 05, 06 y 08 a la v2.1 y aprobar los docs 13 a 16.
- Se retira `docs/arquitectura.md`, un documento anterior al roadmap que contradecía las decisiones vigentes; la arquitectura vigente es el doc 03 del Drive.

## Validación

- Cada archivo de `docs/diseno/` tiene el encabezado con versión y fecha.
- La versión indicada en cada copia coincide con la del documento del Drive.
