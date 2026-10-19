# DEC-020 — Herramientas de gestión y de pruebas: GitHub Projects, Excel del curso y Playwright

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-18 |
| Tarea de origen | PLN-C-02 (decisiones menores pendientes del Sprint 0) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Relacionada con | DEC-017 (metodología), DEC-008 (frontend en TypeScript) |

## Contexto

- DEC-017 exige un Sprint Board y un Burndown por sprint, en el formato del curso.
- El Product Backlog de VAEL (`VAEL/Docs/Scrum/VAEL_Product_Backlog.xlsx`) ya calcula la capacidad del equipo y el Burndown.
- El roadmap prevé pruebas de extremo a extremo (E2E) en el Sprint 2 (TST-A-03) y pruebas de cámara y micrófono en varios navegadores en el ciclo siguiente (TST-B-03).
- El frontend se escribe en TypeScript (DEC-008).

## Decisión

### Tablero y seguimiento

| Herramienta | Uso |
|---|---|
| **GitHub Projects** (en `Vael-Tesis/Vael`) | Sprint Board: una tarjeta por tarea, enlazada con su PR y sus commits. Columnas: Por hacer · En curso · En revisión · Hecho |
| **Excel del curso** (`VAEL_Product_Backlog.xlsx`) | Product Backlog, Planning Poker, estimación en horas, capacidad del equipo y Burndown |

Regla: el Excel es la fuente de las estimaciones y del Burndown; GitHub Projects es la fuente del estado de cada tarea. Al cierre de cada día, el Scrum Master registra en el Burndown las horas restantes según las tarjetas.

### Pruebas de extremo a extremo

**Playwright**, con las pruebas en TypeScript dentro de `frontend/e2e/`, ejecutadas en GitHub Actions.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Jira (plan gratuito) | Herramienta aparte, sin vínculo directo con el código; obliga a mantener dos sistemas de seguimiento |
| Solo el Excel | No enlaza las tareas con el código; el seguimiento diario es manual |
| Cypress | Soporte limitado de WebKit (Safari), relevante para las pruebas por navegador del ciclo siguiente |
| Selenium | Más lento y verboso; requiere más configuración |

## Trade-off aceptado

El seguimiento queda en dos lugares (tablero en GitHub, Burndown en Excel). Se acepta porque cada uno cubre lo que el otro no tiene: la trazabilidad con el código y el formato exigido por el curso.

## Consecuencias

- Sprint Planning del Sprint 1: crear el proyecto en GitHub Projects y cargar las tareas del sprint.
- Doc 04 (stack): las herramientas de tablero y E2E pasan de "por decidir" a vigentes.
- Roadmap: TST-A-03 se implementa con Playwright.
- Monografía, apartado 3.2: GitHub Projects y el Burndown como evidencia de la práctica de Scrum.

## Validación

- Cada tarea del sprint tiene su tarjeta enlazada con su PR.
- El Burndown del Sprint 1 tiene registradas las horas restantes de los 5 días.
- La prueba E2E del flujo principal corre en el CI.
