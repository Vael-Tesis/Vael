import { type Locator, type Page, expect } from '@playwright/test'

/**
 * Credenciales del admin semilla de la empresa A (doc 13). La contraseña nunca va en el
 * repositorio: viene de SEED_PASSWORD_ADMIN o SEED_PASSWORD, igual que
 * `app.scripts.semillas.password_de` en el backend.
 */
export const ADMIN_EMAIL = 'admin@andina.example.com'

export function passwordSemilla(rol: 'ADMIN' = 'ADMIN'): string {
  const valor = process.env[`SEED_PASSWORD_${rol}`] || process.env.SEED_PASSWORD
  if (!valor) {
    throw new Error(`Define SEED_PASSWORD_${rol} o SEED_PASSWORD en el entorno para correr los E2E (ver frontend/e2e/README.md)`)
  }
  return valor
}

/** Inicia sesión como el admin de la empresa A y espera a llegar al dashboard (RF-A-01). */
export async function iniciarSesion(page: Page, email = ADMIN_EMAIL, password = passwordSemilla()): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill(email)
  await page.getByLabel('Contraseña').fill(password)
  await page.getByRole('button', { name: /^Ingresar/ }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
}

/**
 * La fila (de una lista de Cards sin `data-testid`) que contiene el texto exacto dado —
 * el ancestro `div` más cercano que además contiene un botón, para no depender de cuántos
 * `div` envuelven cada tarjeta.
 */
export function fila(page: Page, textoExacto: string): Locator {
  const escapado = JSON.stringify(textoExacto)
  return page.locator(`xpath=(//*[normalize-space(string(.))=${escapado}])[last()]/ancestor::div[.//button][1]`)
}
