import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers'

/**
 * RF-A-02 (DEC-011): la sesión se renueva sin intervención mientras el refresh token es
 * válido. El cliente tipado (`frontend/src/api/cliente.ts`) no renueva por temporizador:
 * reacciona al primer 401 de una petición, pide un par nuevo con `POST /auth/refresh` y
 * reintenta la petición original una sola vez — así que, para probarlo de verdad (y no con
 * el reloj del navegador, que no cambia lo que el backend valida), el access_token tiene que
 * expirar realmente. El job E2E arranca el backend con `ACCESS_TOKEN_EXPIRE_MINUTES=2`
 * (frontend/e2e/README.md): esta prueba tarda poco más de dos minutos a propósito.
 */

test('la sesión se renueva sola cuando el access token expira', async ({ page }) => {
  test.setTimeout(3 * 60 * 1000)

  await iniciarSesion(page)

  // Más que ACCESS_TOKEN_EXPIRE_MINUTES=2 del backend de este job (margen de reloj entre
  // el servidor y el entorno de CI).
  await page.waitForTimeout(2 * 60 * 1000 + 15_000)

  const renovacion = page.waitForResponse((r) => r.url().includes('/api/auth/refresh'))
  await page.getByRole('link', { name: 'Vacantes' }).click()

  const respuestaRenovacion = await renovacion
  expect(respuestaRenovacion.ok()).toBe(true)

  // La persona nunca ve el login: la petición original se reintentó sola con el token nuevo.
  await expect(page).toHaveURL(/\/vacantes$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Vacantes' })).toBeVisible()
})
