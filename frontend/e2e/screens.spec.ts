import { expect, test, type Page } from '@playwright/test'

const OUT = '.screenshots'

test.use({ viewport: { width: 1280, height: 900 } })

async function signIn(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.waitForURL(/\/tickets/)
}

/** Documentation shots, not a check. Run with `npm run screenshots`. */
test('@screens capture every screen', async ({ page }) => {
  await page.goto('/login')
  await page.screenshot({ path: `${OUT}/01-login.png` })

  await signIn(page, 'dispatcher@example.com', 'Dispatcher123!')
  await expect(page.getByText(/\d+ tickets?/)).toBeVisible()
  await page.screenshot({ path: `${OUT}/02-tickets-dispatcher.png` })

  await page.getByRole('link', { name: 'Contractors' }).click()
  await expect(page.getByText(/open job/).first()).toBeVisible()
  await page.screenshot({ path: `${OUT}/03-workers.png` })

  await page.getByRole('link', { name: 'Tickets' }).first().click()
  await page.getByRole('link', { name: /Street light/ }).first().click()
  await expect(page.getByRole('heading', { name: 'Timeline' })).toBeVisible()
  // The recommendation list is the slowest panel; wait for a real score.
  await expect(page.getByRole('button', { name: /\d{2}/ }).first()).toBeVisible()
  await page.screenshot({ path: `${OUT}/04-ticket-detail-dispatcher.png` })

  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, 'reporter@example.com', 'Reporter123!')
  await expect(page.getByText(/\d+ tickets?/)).toBeVisible()
  await page.screenshot({ path: `${OUT}/05-tickets-reporter.png` })

  await page.getByRole('link', { name: 'Report an issue' }).first().click()
  await expect(page.getByLabel('What is wrong?')).toBeVisible()
  await page.getByLabel('What is wrong?').fill('Water leaking in the stairwell')
  await page.getByLabel('Details').fill('Third floor, getting worse since morning.')
  await page.screenshot({ path: `${OUT}/06-new-ticket.png` })

  await page.getByRole('link', { name: 'Notifications' }).click()
  await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible()
  await expect(page.getByRole('listitem').first()).toBeVisible()
  await page.screenshot({ path: `${OUT}/07-notifications.png` })
})
