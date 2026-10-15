# DEC-008 — Frontend: migración incremental a TypeScript con contrato tipado

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-02 (decisión 3) — roadmap `11_roadmap_post_E2.md` v1.1 |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Reemplaza | Doc 04 (frontend en JavaScript reutilizando el de MENTIS) |
| Relacionada con | DEC-007 (los tipos del score provienen del contrato) |

> Documento interno. La versión de esta decisión para la monografía no menciona a MENTIS.

## Contexto

Revisión del repositorio al 2026-10-13 (HECHOS):

- `frontend/` contiene una aplicación React 19 + Vite 8 + Tailwind 4 + TanStack Query + React Router 7, escrita en JavaScript: 17 páginas del perfil Admin, 7 del perfil Candidato y unas 5,200 líneas. `vite build` compila sin errores.
- No es una reutilización del frontend de MENTIS: la similitud línea a línea entre páginas equivalentes es de 2 a 5%.
- El contrato con el backend está desalineado: `EntrevistasIA` llama a `GET /entrevista/lista` (la ruta real es `GET /entrevista`) y `Plantillas` llama a `/entrevista/plantillas` (la ruta real es `/plantillas`).
- 19 archivos usan `devFallback`, que en desarrollo sustituye las respuestas fallidas del backend por datos simulados. Esto oculta los errores anteriores y contradice el criterio "sin mocks en el flujo principal" del roadmap.
- La paleta del frontend (grises e índigo) no coincide con la identidad de VAEL definida en `landing/` (verde de marca `#0E5C4A`).

## Decisión

1. **Base:** se conserva el frontend actual y se migra de forma incremental a **TypeScript en modo estricto**. Durante la transición, `allowJs` permite convivir archivos `.jsx` y `.tsx`.
2. **Contrato tipado:** los tipos y el cliente HTTP se generan desde el OpenAPI de FastAPI (`/openapi.json`) con `openapi-typescript` y `openapi-fetch`. Las rutas, parámetros y cuerpos de cada llamada se verifican al compilar: una ruta inexistente no compila.
3. **Definición de "pantalla migrada":** archivo `.tsx`, consume solo el cliente tipado, sin `any` explícito no justificado, sin mocks y coincide con el Figma.
4. **Mocks:** `devFallback` sale del flujo principal. Los datos simulados solo se activan con `VITE_MOCKS=true` y están desactivados por defecto.
5. **Identidad visual:** las variables CSS se reemplazan por la paleta de VAEL, verificada contra el Figma. Si el Figma y la landing difieren, prevalece el Figma.
6. **Alcance por ciclo:** las páginas Admin se migran en este ciclo (Ruta A). Las páginas Candidato se migran en el ciclo 2 (Ruta B). Al cerrar la Ruta B se desactiva `allowJs`.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| A. Mantener JavaScript y verificar el contrato con un script en el CI | El script solo valida rutas; no valida parámetros ni cuerpos, y no aporta seguridad de tipos al resto de la aplicación |
| C. Reescribir el frontend en TypeScript desde cero tomando a MENTIS como referencia | Descarta unas 5,200 líneas que compilan, con un riesgo alto para el plazo de E3 (viernes 30 de octubre) |
| D. Volver al frontend de MENTIS | Está acoplado al contrato de Django; VAEL ya se separó de él |

## Trade-off aceptado

Durante la transición conviven archivos JavaScript y TypeScript. Las páginas aún no migradas no tienen verificación de tipos; en el perfil Candidato esa situación se mantiene hasta el ciclo 2. Se acepta porque la migración página por página permite avanzar sin detener el desarrollo funcional.

## Consecuencias

Cambios en el roadmap:

| Tarea | Cambio |
|---|---|
| DEV-C-06 (redefinida) | Configurar TypeScript estricto con `allowJs` y migrar la base compartida: cliente API, layouts, componentes `ui/`, `main` y `App`. Aplicar la paleta VAEL y controlar los mocks con `VITE_MOCKS`. CA: `tsc --noEmit` y `vite build` sin errores; `docker-compose up` levanta los 3 servicios |
| DEV-C-09 (nueva) | Generar el cliente tipado desde `/openapi.json` e incorporar al CI los pasos de generación, `tsc --noEmit` y build. CA: el CI falla si el frontend llama a una ruta o envía un campo inexistente |
| DEV-A-01 a DEV-A-10 | El CA de cada pantalla incluye estar migrada según el punto 3 de la decisión |

Documentos a actualizar:
- Doc 04: stack del frontend (TypeScript, generación del cliente, versiones reales: Vite 8, React Router 7, Tailwind 4).
- `CLAUDE.md`: stack del frontend y regla de mocks.
- Roadmap: tareas indicadas arriba y línea base (sección 3).
- Monografía, Capítulo III: presentar esta decisión **sin mencionar a MENTIS**. La Tabla 2.7 del E2 v1.1 registra "React con Vite" sin alternativas evaluadas; el Capítulo III debe completar la decisión con TypeScript, el contrato tipado y las alternativas descartadas.

## Validación

- Antes de corregir las rutas, el frontend migrado con el cliente tipado debe **fallar al compilar** en las dos llamadas desalineadas detectadas. Esa captura, junto con la de la compilación corregida, sirve como evidencia del Capítulo III.
- CI en verde con generación del contrato, `tsc --noEmit` y `vite build`.
- Ninguna pantalla Admin depende de `devFallback` con `VITE_MOCKS` desactivado.
