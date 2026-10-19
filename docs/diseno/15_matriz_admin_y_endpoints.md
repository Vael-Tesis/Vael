> COPIA del documento del Drive `VAEL/Docs/15_matriz_admin_y_endpoints.md`, versión 1.2 — **APROBADO** (2026-10-18), copiada el 2026-10-18.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 15 — Matriz de vistas del perfil Admin y endpoints faltantes

| Campo | Valor |
|---|---|
| Versión | 1.2 — **APROBADO** (2026-10-18) |
| Tareas de origen | PLN-A-01 (matriz) y PLN-A-02 (endpoints faltantes) |
| Criterio | El Figma no es definitivo. **VAEL deriva de MENTIS: sus vistas se asimilan y se adaptan al formato de VAEL** (decisiones DEC-007 a DEC-019, contrato del backend FastAPI, TypeScript) |
| Alcance aprobado | **Todo lo de esta matriz se desarrolla en este ciclo** (perfil Admin completo) |
| Fuentes | Frontend de MENTIS (21 páginas y 3 componentes), frontend de VAEL (17 páginas Admin), 57 rutas del backend de VAEL |

> Documento interno: puede mencionar a MENTIS. La monografía no.

## Cómo leer la matriz

| Decisión | Significado |
|---|---|
| **Asimilar** | La vista de MENTIS se adopta con su comportamiento, adaptada al contrato y al estilo de VAEL |
| **Adaptar** | Se adopta, pero una decisión de VAEL cambia su comportamiento |
| **Nueva** | Vista que MENTIS no tenía y VAEL necesita |

Todas las vistas cumplen el criterio de DEC-008: `.tsx`, cliente tipado, sin mocks, permisos por rol en la interfaz y en el backend.

## Parte 1 — Retrospectiva MENTIS → VAEL (PLN-A-01)

| # | Vista de MENTIS | Vista de VAEL | Decisión | Lo que falta en VAEL | Ajuste por decisiones de VAEL | Historia |
|---|---|---|---|---|---|---|
| V-01 | Login | P-01 Login | Asimilar | — | Refresh transparente y logout efectivo (DEC-011) | HU-01, HU-02 |
| V-02 | *(raíz redirige a vacantes)* | P-02 Dashboard | **Nueva** | — | Pendientes de decisión, minutos de revisión y concordancia | HU-20 |
| V-03 | VacantesList | P-03 Vacantes | Asimilar | Duplicar y eliminar desde el listado | Eliminar solo en borrador | HU-08 |
| V-04 | VacanteForm | P-04 Formulario de vacante | Asimilar | Solo áreas activas | Selector de plantilla de evaluación | HU-08 |
| V-05 | VacanteDetalle | P-05 Detalle de vacante | Asimilar | Textos de publicación guardados y editables | "Despublicar" = pausar; "reactivar" = publicar | HU-09, HU-10 |
| V-06 | CandidatosList | P-06 Candidatos | Asimilar | Botón analizar | Muestra los estados `*_por_confirmar` | HU-11, HU-12 |
| V-07 | CandidatoForm | P-07 Registrar candidato | Asimilar | — | — | HU-11 |
| V-08 | CargaMasiva | P-07 (pestaña) | Asimilar | Solo vacantes abiertas | Pestaña dentro de P-07 | HU-11 |
| V-09 | CandidatoDetalle | P-08 Detalle de candidato | **Adaptar** | Editar y eliminar notas; tags; reanalizar | Acciones de estado por el endpoint de decisiones (DEC-009); historial de decisiones | HU-12, HU-13, HU-16 |
| V-10 | EntrevistaPanel | Dentro de P-08 | Asimilar | Resumen y capturas de la entrevista | Sin emociones (DEC-001) | HU-12 |
| V-11 | AccionesTalento | Dentro de P-08 | **Adaptar** | Descartar con motivo obligatorio; enviar al banco | Descartar = decisión con justificación (DEC-009) y correo de cierre (DEC-013) | HU-14, HU-15 |
| V-12 | *(no existe)* | **P-09 Bandeja de recomendaciones** | **Nueva** | — | Requisitos de diseño abajo | HU-15 |
| V-13 | Ranking | P-10 Ranking | **Adaptar** | Finalistas en lote; filtro por vacante | Decisiones en lote de la etapa `entrevista`; proceso incompleto aparte (DEC-007) | HU-17, HU-18 |
| V-14 | Evaluaciones | P-11 Exámenes | Asimilar | Filtro por vacante | — | HU-19 |
| V-15 | ExamenDetalle | P-12 Detalle de examen | Asimilar | Auditoría en la misma vista | — | HU-19 |
| V-16 | EntrevistasIA | P-13 Entrevistas | Asimilar | — | **Corregir la ruta** (`GET /entrevista`) | HU-19 |
| V-17 | EntrevistaDetalle | P-14 Detalle de entrevista | Asimilar | Galería de capturas | Sin emociones (DEC-001) | HU-19 |
| V-18 | Auditoria | P-15 Auditoría | Asimilar | Navegación por examen | Vista global con eventos de entrevista | HU-19 |
| V-19 | *(no existe)* | P-16 Plantillas | **Nueva** | — | **Corregir la ruta** (`/plantillas`); edición de dimensiones | HU-06 |
| V-20 | Areas | P-17 Áreas | Asimilar | Editar, activar, desactivar y eliminar | Eliminar solo sin vacantes | HU-05 |
| V-21 | BancoTalento | P-18 Banco de talento | Asimilar | Filtro por área; agregar al banco | — | HU-14 |
| V-22 | Usuarios | P-19 Usuarios | Asimilar | Reenviar credenciales | Desactivar invalida la sesión (DEC-011) | HU-07 |

Elementos transversales a asimilar: `ConfirmModal` (confirmación antes de acciones irreversibles) y `ProtectedRoute` (guard de rutas), que en VAEL valida también el rol.

### Requisitos de diseño de la bandeja (P-09)

1. Filtros por vacante y etapa (CV / examen).
2. Por candidato: nombre, puntaje, umbral, recomendación de la IA, justificación y, en examen, semáforo de integridad.
3. Confirmar o decidir lo contrario; lo contrario exige justificación.
4. Confirmación en lote solo de recomendaciones coincidentes.
5. Abrir el detalle registra `revision_inicio` (OE1).
6. Aviso visible: "La IA recomienda; la decisión es tuya".

## Parte 2 — Endpoints faltantes (PLN-A-02)

**Corrección registrada:** la v1.1 habló de "14 endpoints". El conteo correcto es **16 endpoints nuevos**: 9 de la retrospectiva, 6 de etiquetas y 1 de métricas. A ellos se suman los 4 de decisiones (DEC-009) y el endpoint interno de las Lambdas (DEC-018), especificados en el doc 06.

### Derivados de la retrospectiva (9)

| Método | Ruta | Permiso | Función | Historia |
|---|---|---|---|---|
| DELETE | `/api/vacantes/{vacante_id}` | Reclutador+ | Elimina una vacante **solo en borrador** (409 en otro estado) | HU-08 |
| GET | `/api/vacantes/{vacante_id}/textos` | Autenticado | Devuelve los textos de publicación guardados | HU-10 |
| PUT | `/api/vacantes/{vacante_id}/textos` | Reclutador+ | Guarda los textos de publicación editados | HU-10 |
| PUT | `/api/candidatos/{candidato_id}/notas/{nota_id}` | Autor de la nota | Edita una nota propia | HU-13 |
| DELETE | `/api/candidatos/{candidato_id}/notas/{nota_id}` | Autor o admin | Elimina una nota | HU-13 |
| POST | `/api/candidatos/{candidato_id}/banco-talento` | Reclutador+ | Marca al candidato como disponible en el banco de talento | HU-14 |
| POST | `/api/areas/{area_id}/activar` | Admin o gerente | Activa el área | HU-05 |
| POST | `/api/areas/{area_id}/desactivar` | Admin o gerente | Desactiva el área | HU-05 |
| DELETE | `/api/areas/{area_id}` | Admin | Elimina el área solo si no tiene vacantes (409 si tiene) | HU-05 |

Cambios de modelo asociados (doc 05 v2.1): `Vacante.textos_publicacion`, `Candidato.en_banco_talento` y `NotaCandidato.updated_at`.

### Etiquetas (6)

| Método | Ruta | Permiso | Función |
|---|---|---|---|
| GET | `/api/tags` | Autenticado | Lista las etiquetas de la empresa |
| POST | `/api/tags` | Reclutador+ | `{ "nombre": str(≤50), "color": "#RRGGBB" }`; 409 si el nombre ya existe |
| PUT | `/api/tags/{tag_id}` | Reclutador+ | Edita nombre o color |
| DELETE | `/api/tags/{tag_id}` | Admin o gerente | Elimina la etiqueta y sus asignaciones |
| POST | `/api/candidatos/{candidato_id}/tags` | Reclutador+ | `{ "tag_id": str }`; idempotente |
| DELETE | `/api/candidatos/{candidato_id}/tags/{tag_id}` | Reclutador+ | Quita una etiqueta |

### Métricas del dashboard (1)

`GET /api/metricas/dashboard?desde=&hasta=` — Autenticado. Vacantes y candidatos por estado, recomendaciones pendientes por etapa, postulaciones por día, minutos promedio de revisión (OE1) y tasa de concordancia (M-02).

### Alta de empresa — DEC-015

Sin endpoint: `python -m app.scripts.crear_empresa`.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-14 | Borrador construido desde el código de VAEL |
| 1.1 | 2026-10-16 | Retrospectiva MENTIS → VAEL |
| 1.2 | 2026-10-18 | Aprobado; alcance completo en este ciclo; historias asociadas; corrección del conteo (16 endpoints nuevos, no 14) |
