import { defineConfig, devices } from '@playwright/test'

/**
 * Configuración de Playwright (DEC-020, TST-A-03). Las pruebas asumen que el backend
 * (con las semillas del doc 13 cargadas) y el frontend ya están corriendo — ver
 * frontend/e2e/README.md para levantarlos en local, o el job `e2e` del CI.
 *
 * Solo Chromium (DEC-020): WebKit y los demás navegadores quedan para TST-B-03.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // el flujo principal comparte datos semilla entre pruebas del mismo archivo
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
