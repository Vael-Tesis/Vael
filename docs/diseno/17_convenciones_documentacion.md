> COPIA del documento del Drive `VAEL/Docs/17_convenciones_documentacion.md`, versión 1.1 — Propuesta para revisión del equipo, copiada el 2026-10-28.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 17 — Convenciones de documentación

| Campo | Valor |
|---|---|
| Versión | 1.1 — Propuesta para revisión del equipo |
| Actualizado | 2026-10-28 |
| Aplica a | Toda la documentación de VAEL: Drive `VAEL/Docs`, `docs/decisiones/`, `docs/diseno/`, `CLAUDE.md` y artefactos de Scrum |
| Lo usan | Las personas del equipo, **Claude Code** (en el repositorio) y **Claude en el chat** (con el conector de Drive) |
| Copia en el repositorio | `docs/diseno/17_convenciones_documentacion.md` (DEC-019) |

Este documento es la referencia única de cómo se documenta en VAEL. **Un agente de IA que documente debe leerlo completo antes de crear o modificar cualquier documento**, y recorrer el checklist de la sección 11 antes de dar el trabajo por terminado.

---

## 1. Fuentes de verdad

| Contenido | Fuente de verdad | Copias |
|---|---|---|
| Diseño, arquitectura, roadmap, métricas, monografía | Drive `VAEL/Docs` | `docs/diseno/` (solo docs 05, 06, 07, 08, 13 a 17) |
| Decisiones DEC-007 en adelante | Repositorio, `docs/decisiones/` | Listadas en el roadmap, sección 4 |
| Instrucciones para Claude Code | `CLAUDE.md` (derivado del Drive y de los ADR) | — |
| Backlog, estimaciones, Burndown | `VAEL/Docs/Scrum/VAEL_Product_Backlog.xlsx` | — |
| Estado de cada tarea | GitHub Projects (DEC-020) | — |

**Las copias de `docs/diseno/` nunca se editan.** Se cambia el documento del Drive y se vuelve a copiar con el script.

---

## 2. Formato de los archivos

1. **Solo Markdown (`.md`)**, codificación UTF-8.
2. **Editar los `.md` en un editor de texto** (VS Code, IntelliJ, Bloc de notas) y subirlos como archivo nuevo. No convertirlos a documento de Google Docs: dejarían de ser Markdown y el script de sincronización no podría leerlos.
3. **Primera sección:** tabla de metadatos `| Campo | Valor |` con, como mínimo, `Versión` y `Actualizado`. El script de sincronización lee la fila `Versión`.
4. **Última sección:** tabla `## Historial` con `| Versión | Fecha | Cambio |`. Cada versión agrega una fila; nunca se borran filas.
5. Fechas en formato `AAAA-MM-DD`.

---

## 3. Versionado

| Tipo de cambio | Versión | Ejemplo |
|---|---|---|
| Corrección, agregado o actualización de estado que no cambia el sentido del documento | Menor: 2.1 → 2.2 | Marcar como "Implementado" lo que se construyó |
| Reestructuración, o cambio por una decisión que modifica lo que el documento establece | Mayor: 2.2 → 3.0 | Un flujo que cambia por una decisión nueva |

**Procedimiento:**
1. Se crea el archivo nuevo **con el mismo nombre** (por ejemplo, `05_modelos_bd.md`), con la versión nueva en la tabla de metadatos y una fila nueva en el historial.
2. El archivo anterior se renombra con su versión (`05_modelos_bd_v2.1.md`) y **se mueve a `Docs/_historial`**.
3. **Nunca se borra una versión anterior.** Es la evidencia de la evolución del proyecto.

**Propiedad de los archivos:** en el Drive, solo el propietario de un archivo puede moverlo. Si quien actualiza un documento no es el propietario de la versión anterior, la **copia** a `Docs/_historial` con el sufijo y **avisa al propietario** para que retire el original de la carpeta `Docs`. Nunca deja en `Docs` el original renombrado.

---

## 4. Estados en los documentos técnicos

| Estado | Uso |
|---|---|
| **Implementado** | Existe en el código integrado en `develop` |
| **Cambia (tarea · historia)** | Existe, pero una decisión cambia su comportamiento |
| **Planificado (tarea · historia)** | Definido; aún no existe |
| **Se elimina (tarea)** | Existe y se retirará |

Al integrar una historia, los elementos que construyó pasan de "Planificado" o "Cambia" a **"Implementado"** en los documentos afectados.

---

## 5. Redacción

1. **Español.**
2. **Siglas:** su significado entre paréntesis la primera vez que aparecen en cada documento. Ejemplo: PR (*Pull Request*, solicitud de integración).
3. **Cifras:** con fuente verificable, o marcadas como **HIPÓTESIS** o **SUPUESTO**. Nunca se inventa una cifra ni una fuente.
4. **Distinguir el tipo de afirmación** cuando importa: HECHO (verificable en el código o en una fuente), DECISIÓN (aprobada), SUPUESTO (no comprobado), PROPUESTA (pendiente de aprobación), HIPÓTESIS (requiere validación).
5. **MENTIS** solo en la documentación interna; **nunca en los capítulos de la monografía ni en el código fuente**.
6. Toda decisión se presenta con sus **alternativas descartadas** y su **trade-off**.

---

## 6. Matriz de coherencia: qué actualizar según el cambio

| Si cambia… | Actualizar |
|---|---|
| Una tabla, campo, estado o política de RLS | Doc 05; doc 06 si afecta a la API |
| Un endpoint, ruta, permiso o contrato | Doc 06; doc 15 si afecta a una vista; `CLAUDE.md` si cambia una regla |
| Un servicio o el flujo del proceso | Doc 08 y doc 07 |
| La infraestructura en AWS, o la lista cerrada de operaciones del sistema | Docs 03 y 09 |
| Una dependencia o una herramienta | Doc 04 |
| Un requerimiento o su criterio de aceptación | Doc 16 y el Product Backlog |
| Una métrica o su forma de medirla | Doc 14 |
| Los datos semilla | Doc 13 |
| **Una decisión nueva** | ADR en `docs/decisiones/`, su índice (`README.md`), la sección 4 del roadmap y todos los documentos que la decisión diga en "Consecuencias" |
| El avance de las tareas | Roadmap, sección 11 (registro de avance) |
| **Cualquier documento del Drive** | Doc 00 (índice): versión vigente |
| Docs 05, 06, 07, 08 o 13 a 17 | Ejecutar `scripts/sincronizar-diseno.ps1` y abrir un PR con `docs/diseno/` |

---

## 7. Decisiones (ADR)

**ADR** (*Architecture Decision Record*, registro de decisión de arquitectura). Archivo `docs/decisiones/DEC-NNN-<titulo-corto>.md`, con el número siguiente al último del índice.

**Plantilla obligatoria:**

```markdown
# DEC-NNN — <Título>

| Campo | Valor |
|---|---|
| Estado | Propuesta / Aprobada / Reemplazada por DEC-MMM |
| Fecha | AAAA-MM-DD |
| Tarea de origen | <ID> |
| Decidido por | <quiénes> |
| Modifica / Reemplaza | <DEC o documento, si aplica> |

## Contexto
## Decisión
## Alternativas descartadas
## Trade-off aceptado
## Consecuencias
## Validación
```

**Reglas:**
1. Una decisión nace con estado **Propuesta**. Pasa a **Aprobada** cuando el otro integrante la aprueba en la revisión del PR.
2. Una decisión aprobada no se edita para cambiar su sentido: una decisión nueva la modifica o la reemplaza, y lo indica.
3. Toda decisión nueva se agrega al índice `docs/decisiones/README.md` y actualiza el número siguiente.

---

## 8. Artefactos de Scrum (DEC-017)

Todos en `VAEL/Docs/Scrum`.

| Artefacto | Archivo | Cuándo | Responsable |
|---|---|---|---|
| Sprint Planning | `Sprint-N_Planning.md` | Antes y durante la reunión del lunes; el registro se completa al terminar la reunión | Scrum Master |
| Burndown | `VAEL_Product_Backlog.xlsx`, hoja BURNDOWN | Al final de cada día | Scrum Master |
| Estado de tareas | GitHub Projects | Al cambiar el estado de una tarea | Quien la toma |
| Sprint Review | `Sprint-N_Review.md` | Viernes, al cierre | Product Owner |
| Retrospectiva | `Sprint-N_Retrospectiva.md` | Viernes, al cierre | Scrum Master |

**Contenido mínimo de la Sprint Review:** objetivo del sprint y si se cumplió; historias terminadas según la *Definition of Done*; historias no terminadas y su destino; requerimientos verificados con su resultado; PR integrados; decisiones tomadas en el sprint; horas comprometidas frente a horas reales.

**Contenido mínimo de la Retrospectiva:** qué funcionó; qué no funcionó; acciones concretas, cada una con responsable y sprint en que se aplica; seguimiento de las acciones de la retrospectiva anterior.

**El registro es honesto:** si algo no ocurrió como estaba planificado (una reunión que no se hizo, un objetivo que no se cumplió), se registra así. Un registro reconstruido después de los hechos se marca como tal, con su fecha.

---

## 9. Uso con Claude Code (en el repositorio)

Claude Code **no tiene acceso al Drive**. Por eso:

1. Lee las copias de `docs/diseno/`, los ADR de `docs/decisiones/` y `CLAUDE.md`.
2. Si una tarea exige actualizar un documento del Drive, **genera la versión nueva completa** en la carpeta `drive_pendiente/` del repositorio, ignorada por Git, con el mismo nombre del documento y aplicando las secciones 2 a 6.
3. Informa al final de la tarea qué documentos dejó en `drive_pendiente/` y qué versión tienen.
4. La persona los sube al Drive, archiva las versiones anteriores (sección 3), vacía `drive_pendiente/` y ejecuta el script de sincronización.
5. Los ADR sí los escribe directamente en `docs/decisiones/`, porque viven en el repositorio.
6. **Nunca edita `docs/diseno/`.**

---

## 10. Uso con Claude en el chat (con el conector de Drive)

1. Antes de documentar, lee este documento y el doc 00 (índice).
2. El conector no edita el contenido de un archivo existente: **crea el archivo nuevo** con el mismo nombre y la versión nueva.
3. Renombra el archivo anterior con su versión y lo mueve a `Docs/_historial`. Si no es el propietario y el Drive lo rechaza, aplica la regla de propiedad de la sección 3 e **informa qué originales quedaron pendientes de retirar**.
4. Actualiza el doc 00.
5. Indica qué documentos cambiaron que tienen copia en `docs/diseno/`, para ejecutar el script y abrir el PR.

**Nota sobre la lectura:** al leer un `.md` con el conector, el texto puede aparecer con barras invertidas delante de los símbolos de Markdown (`\#`, `\*\*`). Es un efecto de la herramienta de lectura, no un daño del archivo.

---

## 11. Checklist de cierre de una actualización de documentación

Antes de dar por terminado el trabajo, verificar:

- [ ] Cada documento modificado tiene la versión nueva en su tabla de metadatos y una fila nueva en el historial.
- [ ] Cada versión anterior está en `Docs/_historial`, con su sufijo, y ningún original renombrado quedó en `Docs`.
- [ ] Los documentos siguen siendo archivos `.md`, no documentos convertidos de Google Docs.
- [ ] Se aplicó la matriz de la sección 6: no queda ningún documento afectado sin actualizar.
- [ ] Lo construido figura como "Implementado".
- [ ] Toda decisión nueva tiene su ADR, está en el índice de decisiones y en la sección 4 del roadmap.
- [ ] El doc 00 refleja las versiones vigentes.
- [ ] Si cambió un documento con copia en `docs/diseno/`, se ejecutó el script y se abrió el PR.
- [ ] Las siglas tienen su significado la primera vez; las cifras tienen fuente o están marcadas como hipótesis.
- [ ] Los artefactos de Scrum del sprint están completos y son honestos.

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-27 | Propuesta inicial: reúne las convenciones dispersas; matriz de coherencia, plantillas de Scrum y uso con Claude Code y Claude en el chat |
| 1.1 | 2026-10-28 | **Corrección:** se retira la afirmación de que Google Docs corrompe los `.md` (era un efecto de la herramienta de lectura; se agrega la nota de la sección 10). Regla de propiedad de archivos al archivar versiones (sección 3), tras el caso de los originales renombrados que quedaron en `Docs`. La lista cerrada de operaciones del sistema se agrega a la matriz (docs 03 y 09) |
