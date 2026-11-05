# E2E (Playwright) — TST-A-03, HU-25, DEC-020

Pruebas de extremo a extremo del flujo principal del perfil Admin, en TypeScript, contra
el backend real y los datos semilla del doc 13 (no hay mocks: DEC-008). Solo Chromium
(DEC-020); WebKit y los demás navegadores quedan para TST-B-03.

## Qué cubren

- `flujo-principal.spec.ts`: login (RF-A-01) → dashboard → vacante → candidato con su
  análisis de IA (RF-A-10) → bandeja: confirmar una recomendación (RF-A-11) → historial de
  decisiones (RF-A-12) → ranking: decidir un finalista (RF-A-14, RF-A-15) → cerrar sesión.
- `renovacion-sesion.spec.ts`: RF-A-02, la renovación transparente de la sesión cuando el
  access token expira en pleno uso (tarda poco más de dos minutos a propósito — ver abajo).

## Cómo correrlas en local

1. Levanta la base, S3 local y el correo local (DEC-023), y carga las semillas (doc 13),
   igual que en el desarrollo normal (CLAUDE.md, sección 15):

   ```bash
   docker-compose up -d db s3mock mailpit
   cd backend
   python -m app.scripts.crear_roles
   alembic upgrade head
   SEED_PASSWORD=una-clave-de-prueba python -m app.scripts.semillas
   ```

2. Arranca el backend **con un access token de 2 minutos**, para poder correr
   `renovacion-sesion.spec.ts` sin esperar los 15 minutos reales (DEC-011):

   ```bash
   ACCESS_TOKEN_EXPIRE_MINUTES=2 uvicorn app.main:app --port 8000
   ```

   Para correr solo `flujo-principal.spec.ts` (no hace falta esperar la renovación), el
   valor normal de `.env` (15 minutos) funciona igual.

3. En otra terminal, arranca el frontend (el proxy de `/api` ya apunta a `localhost:8000`,
   `vite.config.js`):

   ```bash
   cd frontend
   npm run dev
   ```

4. En una tercera terminal, con la misma `SEED_PASSWORD` del paso 1:

   ```bash
   cd frontend
   SEED_PASSWORD=una-clave-de-prueba npm run e2e
   ```

   `npx playwright show-report` abre el reporte HTML con las capturas y el trace de
   cualquier prueba que haya fallado.

## Variables de entorno que leen las pruebas

| Variable | Uso | Default |
|---|---|---|
| `E2E_BASE_URL` | URL del frontend (`playwright.config.ts`) | `http://localhost:5173` |
| `SEED_PASSWORD` / `SEED_PASSWORD_ADMIN` | Contraseña del admin semilla (`helpers.ts`), la misma que usó `app.scripts.semillas` | — (obligatoria) |

## Por qué un solo worker y un solo archivo para el flujo principal

`playwright.config.ts` fija `workers: 1` y `fullyParallel: false`: el flujo principal es
una sola prueba con varios `test.step()` que comparten la sesión y los datos semilla
(Sofía Ramírez Cueva para la bandeja, Patricia Nolasco Vega para el ranking — ver
`app.scripts.semillas._candidato_pendiente_bandeja` y `CANDIDATOS_TI_COMPLETOS`, doc 13).
Dividirla en pruebas independientes no ganaría paralelismo real (seguirían dependiendo del
mismo estado) y perdería la narrativa del flujo en el reporte.
