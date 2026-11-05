import { expect, test } from '@playwright/test'
import { fila, iniciarSesion } from './helpers'

/**
 * TST-A-03 (HU-25, DEC-020): flujo principal del perfil Admin con los datos semilla (doc 13).
 *
 * login → dashboard (RF-A-01) → vacante → candidato con su análisis → bandeja: confirmar una
 * recomendación → historial de decisiones → ranking: decidir un finalista → cerrar sesión.
 *
 * Usa dos candidatos sembrados a propósito para este flujo (doc 13, `app.scripts.semillas`):
 * - Sofía Ramírez Cueva: queda en `cv_por_confirmar` sin decidir, para la bandeja.
 * - Patricia Nolasco Vega: `entrevista_realizada` sin decisión, la mejor `score_final` de
 *   TI-2026-001 — el ranking la recomienda como finalista (DEC-022).
 *
 * Un único test: cada paso depende del anterior (misma sesión, mismos datos de la semilla),
 * así que dividirlo en varios perdería ese orden sin ganar nada (`fullyParallel: false`,
 * `workers: 1` en playwright.config.ts).
 */

test('flujo principal del Admin con los datos semilla', async ({ page }) => {
  await test.step('login → dashboard (RF-A-01)', async () => {
    await iniciarSesion(page)
  })

  await test.step('vacante: Desarrollador Backend Python (TI-2026-001)', async () => {
    await page.getByRole('link', { name: 'Vacantes' }).click()
    await expect(page).toHaveURL(/\/vacantes$/)
    await fila(page, 'Desarrollador Backend Python').getByRole('button', { name: 'Ver' }).click()
    await expect(page.getByText('TI-2026-001')).toBeVisible()
  })

  await test.step('candidato con su análisis de IA (RF-A-10)', async () => {
    await page.getByRole('link', { name: 'Candidatos' }).click()
    await expect(page).toHaveURL(/\/candidatos$/)
    await page.getByLabel('Buscar').fill('Patricia Nolasco')
    await fila(page, 'Patricia Nolasco Vega').getByRole('button', { name: 'Ver' }).click()

    await expect(page.getByText('Altamente recomendado')).toBeVisible()
    await expect(page.getByText(/Backend sólido en Python con FastAPI y PostgreSQL/)).toBeVisible()
    await expect(page.getByText('FastAPI', { exact: true })).toBeVisible()
  })

  await test.step('bandeja: confirmar la recomendación de Sofía (RF-A-11)', async () => {
    await page.getByRole('link', { name: 'Bandeja de decisiones' }).click()
    await expect(page).toHaveURL(/\/bandeja$/)

    const filaSofia = fila(page, 'Sofía Ramírez Cueva')
    await expect(filaSofia.getByText('IA recomienda avanzar')).toBeVisible()
    await filaSofia.getByRole('button', { name: 'Revisar' }).click()
    // El panel de decisión se expande como hermano de la fila dentro de la misma tarjeta, no
    // como descendiente de `filaSofia`; y es el único expandido a la vez (solo un `abierto`).
    await page.getByRole('button', { name: /^Confirmar: avanzar/ }).click()

    await expect(page.getByText('Decisión registrada: el candidato avanza')).toBeVisible()
    // La bandeja se actualiza sola (invalidación de la query): Sofía ya no aparece pendiente.
    await expect(page.getByText('Sofía Ramírez Cueva')).toHaveCount(0)
  })

  await test.step('historial de decisiones de Sofía (RF-A-12)', async () => {
    await page.getByRole('link', { name: 'Candidatos' }).click()
    await page.getByLabel('Buscar').fill('Sofía Ramírez')
    await fila(page, 'Sofía Ramírez Cueva').getByRole('button', { name: 'Ver' }).click()

    await page.getByRole('tab', { name: 'Historial de decisiones' }).click()
    await expect(page.getByText('Avanzó')).toBeVisible()
    await expect(page.getByText('CV', { exact: true })).toBeVisible()
  })

  await test.step('ranking: decidir a Patricia como finalista (RF-A-14, RF-A-15)', async () => {
    await page.getByRole('link', { name: 'Ranking' }).click()
    await expect(page).toHaveURL(/\/ranking$/)
    await page.getByRole('combobox').selectOption({ label: 'Desarrollador Backend Python' })

    const filaPatricia = fila(page, 'Patricia Nolasco Vega')
    await expect(filaPatricia.getByText('Finalista')).toBeVisible()
    await filaPatricia.getByRole('button', { name: 'Decidir' }).click()
    // Igual que en la bandeja: el panel de decisión es hermano de la fila, no descendiente.
    await page.getByRole('button', { name: /^Confirmar: marcar como finalista/ }).click()

    await expect(page.getByText('Decisión registrada: el candidato avanza')).toBeVisible()
  })

  await test.step('cerrar sesión (RF-A-02)', async () => {
    await page.getByTitle('Cerrar sesión').click()
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByText('Sesión cerrada')).toBeVisible()
  })
})
