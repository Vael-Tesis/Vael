# DEC-017 — Metodología: plan por fases con ejecución en sprints semanales basada en Scrum

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-16 |
| Tarea de origen | PLN-C-02; apartado 3.2 de la monografía (índice oficial Tecsup) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Modifica | Roadmap v1.2: las etapas PLN, DEV, TST y DEP dejan de ser fases secuenciales de la ruta y pasan a ser tipos de tarea dentro de cada sprint |
| Formato de referencia | Plantillas del curso en `VAEL/Docs/Scrum` (Product Backlog, iteraciones, Sprint Board, Burn Down) |

## Contexto

- **HECHO:** el roadmap v1.2 organiza cada ruta en etapas secuenciales (Planificación → Desarrollo → Testing → Despliegue), un modelo en cascada. El despliegue en AWS y las pruebas integrales quedan para la última semana antes de E3.
- **HECHO:** el formato del curso aplica Scrum: Product Backlog (épicas, historias de usuario, criterios de aceptación), estimación con Planning Poker, sprints de 2 semanas, Sprint Board y Burn Down.
- **Condiciones de VAEL en este ciclo:** fecha fija (E3, 30 de octubre), alcance fijo y detallado (perfil Admin completo, RF-A-01 a RF-A-20), baja incertidumbre técnica en la Ruta A, alto riesgo de integración (AWS, RLS, Lambda, red), equipo de dos personas a tiempo parcial y sin cliente real.
- La Guía de Scrum (Schwaber y Sutherland, 2020) establece que sus roles, eventos y artefactos no se modifican y que aplicar solo una parte no es Scrum.

## Decisión

Se adopta un **enfoque iterativo e incremental basado en Scrum**, en dos niveles:

### Nivel de plan

El roadmap es el plan del ciclo: alcance, decisiones, calendario de entregables y dependencias. La etapa de Planificación ya ejecutada corresponde al **Pre-Sprint (Sprint 0)** del formato del curso. El Gantt del apartado 3.3 se construye desde este nivel.

### Nivel de ejecución

| Elemento | Definición en VAEL |
|---|---|
| Duración del sprint | **1 semana** (lunes a viernes) |
| Product Backlog | Épicas → historias de usuario (derivadas de RF-A) → criterios de aceptación → tareas con horas, en el formato de la plantilla del curso |
| Estimación | Planning Poker con la escala de la plantilla (0.5, 1, 2, 3, 5, 8, 13, 20) |
| Sprint Planning | Lunes, máximo 1 hora: se eligen las historias y se calcula la capacidad del equipo en horas |
| Seguimiento diario | Asíncrono: un mensaje breve por integrante (qué hizo, qué hará, qué lo bloquea) |
| Sprint Review | Viernes, con el incremento funcionando |
| Retrospectiva | Viernes, 30 minutos, con acciones registradas |
| Artefactos de seguimiento | Sprint Board y Burn Down por sprint |
| Roles | **Product Owner: Gabriel Llanos. Scrum Master: Diego Nina.** Ambos forman el equipo de desarrollo. El asesor actúa como interesado en las revisiones de los entregables |

**Definition of Done** de cada historia:
1. Código integrado a `develop` mediante PR revisado por el otro integrante.
2. CI en verde: lint, tests, `tsc --noEmit` y build.
3. Criterio de aceptación verificado.
4. Pruebas de la historia escritas y en verde.
5. Documentos del Drive actualizados si cambió el contrato o el modelo.
6. Desplegada en el entorno de AWS, una vez que este existe (desde el cierre del Sprint 1).

### Calendario de sprints

| Sprint | Fechas | Objetivo | Revisión |
|---|---|---|---|
| Sprint 0 (Pre-Sprint) | Semana 9 | Planificación: decisiones, documentos, backlog | Cierre de la Planificación |
| Sprint 1 | 19–23 oct | RF-A-01 a RF-A-13 con sus pruebas + **esqueleto desplegado en AWS** | **H-50** |
| Sprint 2 | 26–30 oct | RF-A-14 a RF-A-20, despliegue completo y suite de aislamiento | **E3** |
| Sprints 3 a 7 | Semanas 12–16 | Por planificar (consolidación, pre-sustentación) | — |
| Ciclo siguiente | — | Ruta B (perfil Candidato) | — |

### Cambio de mayor impacto

El despliegue deja de ser la última fase: **al cierre del Sprint 1 debe existir un esqueleto desplegado en AWS** (autenticación y al menos un flujo con base de datos real, RLS y pipeline). Así, los riesgos de integración aparecen con diez días de margen antes de E3.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Cascada (roadmap v1.2) | Deja la integración, las pruebas integrales y el despliegue al final, sin margen ante fallas |
| Scrum según la guía, sin adaptaciones | Supone requisitos cambiantes y un Product Owner con cliente; con dos personas, los roles y eventos completos generan una carga desproporcionada |
| Kanban | No ofrece cortes que coincidan con los entregables ni los artefactos del formato del curso |
| Sprints de 2 semanas (formato del curso) | Hasta E3 solo cabría un sprint, sin oportunidad de revisar y ajustar |

## Trade-off aceptado

- Carga de gestión de unas 2 a 3 horas semanales.
- En la monografía no se declara "Scrum" a secas, sino **"un enfoque iterativo e incremental basado en Scrum"**, explicando las adaptaciones (duración del sprint, seguimiento asíncrono, roles compartidos) y su motivo. La declaración debe coincidir con la práctica.

## Consecuencias

| Elemento | Cambio |
|---|---|
| Roadmap v1.3 | Se reorganiza por sprints. Las tareas DEV, TST y DEP se asignan al sprint en que se ejecutan |
| Decisión de topología AWS | **Se adelanta:** debe cerrarse antes del inicio del Sprint 1 (lunes 19 de octubre), porque el esqueleto se despliega en ese sprint |
| DEP-C-01 a DEP-C-05 | Pasan al Sprint 1, en versión mínima |
| TST | Las pruebas de cada historia forman parte de su Definition of Done; TST-C-01 (aislamiento) se construye de forma incremental |
| Nuevo artefacto | Product Backlog de VAEL en el formato del curso |
| Monografía | Apartado 3.2 (metodología) y 3.3 (Gantt por sprints) |
| Pendiente | Herramienta del tablero (propuesta: GitHub Projects, que enlaza historias con PRs y commits) |

## Validación

- Existe un Product Backlog con épicas, historias, criterios y estimaciones.
- Cada sprint tiene su planificación, su tablero, su burndown, su revisión y su retrospectiva registrados.
- Al cierre del Sprint 1 hay un esqueleto desplegado en AWS y el H-50 se revisa con los RF-A-01 a RF-A-13.
- El historial de PRs y commits permite rastrear cada historia hasta su código.
