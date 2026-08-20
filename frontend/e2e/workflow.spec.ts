import { expect, test, type Page } from '@playwright/test'

/**
 * The whole product in one pass: a reporter files an issue, a dispatcher sends it
 * to a contractor, that contractor works it, and the dispatcher closes it.
 *
 * It runs against the real API with the seeded accounts, so it fails the moment
 * the UI and the backend disagree about who may do what.
 */

const SEEDED = {
  reporter: { email: 'reporter@example.com', password: 'Reporter123!' },
  dispatcher: { email: 'dispatcher@example.com', password: 'Dispatcher123!' },
}

/**
 * The test registers its own contractor rather than using a seeded one.
 *
 * A development database accumulates people, and two of them are already called
 * "Ahmed Contractor" — picking a worker by name from that list is ambiguous, and
 * picking the wrong one leaves the test holding a password it cannot use.
 */
const CONTRACTOR = {
  name: 'Nadia Endtoend',
  email: 'e2e-contractor@example.com',
  password: 'Contractor123!',
}

async function signIn(page: Page, account: { email: string; password: string }) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/tickets/)
}

async function signOut(page: Page) {
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/login/)
}

/** Registers the contractor on the first run, and signs in on every run after. */
async function ensureContractor(page: Page) {
  await page.goto('/register')
  await page.getByLabel('Full name').fill(CONTRACTOR.name)
  await page.getByLabel('Email').fill(CONTRACTOR.email)
  await page.getByLabel('Password').fill(CONTRACTOR.password)
  await page.getByRole('radio', { name: /Elevator Technician|Technician/ }).check()
  await page.getByRole('button', { name: 'Elevator emergency', exact: true }).click()
  await page.getByRole('button', { name: 'Create account' }).click()

  const alreadyExists = page.getByRole('alert')
  await expect(alreadyExists.or(page.getByRole('button', { name: 'Sign out' })))
    .toBeVisible()

  if (await alreadyExists.isVisible()) {
    await expect(alreadyExists).toContainText(/already exists/i)
    await signIn(page, CONTRACTOR)
  }

  await expect(page).toHaveURL(/\/tickets/)
}

test('a trapped-person ticket travels from report to closure', async ({ page }) => {
  const title = `People trapped in ELV-02 (${Date.now()})`
  let ticketUrl = ''

  await test.step('a technician signs up for field work', async () => {
    await ensureContractor(page)
    await expect(page.getByRole('link', { name: 'My jobs' })).toBeVisible()
    await signOut(page)
  })

  await test.step('the reporter files an entrapment', async () => {
    await signIn(page, SEEDED.reporter)

    await page.getByRole('link', { name: 'Report an incident' }).first().click()
    await page.getByRole('radio', { name: /PERSON TRAPPED/i }).check()
    await page.getByLabel('How many people?').fill('2')
    await page.getByLabel('Which building?').selectOption('Building A')
    await page.getByLabel('Which elevator?').selectOption('ELV-02')
    await page.getByLabel('Known floor?').fill('7')
    await page.getByLabel('Short summary').fill(title)
    await page.getByLabel('Additional information').fill('Can hear voices.')
    await page.getByRole('button', { name: 'Submit emergency' }).click()

    await expect(page.getByRole('heading', { name: new RegExp(title) })).toBeVisible()
    await expect(page.getByText('Person trapped', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('Critical', { exact: true }).first()).toBeVisible()
    ticketUrl = page.url()

    await expect(page.getByRole('button', { name: 'Assign', exact: true })).toHaveCount(0)
    await signOut(page)
  })

  await test.step('the dispatcher assigns it', async () => {
    await signIn(page, SEEDED.dispatcher)
    await page.goto(ticketUrl)

    await expect(page.getByRole('heading', { name: 'Assign this job' })).toBeVisible()
    await page.getByRole('button', { name: new RegExp(CONTRACTOR.name) }).click()
    await page.getByLabel(/Notes for the/).fill('Access code 4432')
    await page.getByRole('button', { name: 'Assign', exact: true }).click()

    await expect(page.getByText('Assigned', { exact: true }).first()).toBeVisible()
    await expect(page.getByText(CONTRACTOR.name).first()).toBeVisible()
    await signOut(page)
  })

  await test.step('the contractor works it', async () => {
    await signIn(page, CONTRACTOR)

    // Reached through their own queue, so the assignment really is visible there.
    await page.getByRole('link', { name: 'My jobs' }).click()
    await page.getByRole('link', { name: title }).click()

    await page.getByRole('button', { name: 'Accept this job' }).click()
    await expect(page.getByRole('button', { name: 'Start work' })).toBeVisible()

    await page.getByRole('button', { name: 'Start work' }).click()
    await expect(page.getByText('In progress', { exact: true }).first()).toBeVisible()

    await page.getByLabel('Comment').fill('Lamp replaced')
    await page.getByRole('button', { name: 'Mark resolved' }).click()
    await expect(page.getByText('Resolved', { exact: true }).first()).toBeVisible()

    // Closing is the dispatcher's call, never the contractor's.
    await expect(page.getByRole('button', { name: 'Close ticket' })).toHaveCount(0)
    await signOut(page)
  })

  await test.step('the dispatcher closes it', async () => {
    await signIn(page, SEEDED.dispatcher)
    await page.goto(ticketUrl)

    await page.getByRole('button', { name: 'Close ticket' }).click()
    await expect(page.getByText('Closed', { exact: true }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Close ticket' })).toHaveCount(0)

    // The timeline is the audit trail: every step above should be on it.
    for (const action of [
      'Ticket created',
      'Assigned',
      'Assignment accepted',
      'Work started',
      'Resolved',
      'Closed',
    ]) {
      await expect(page.getByText(action, { exact: true }).first()).toBeVisible()
    }
  })
})

test('a reporter is kept out of the dispatcher screens', async ({ page }) => {
  await signIn(page, SEEDED.reporter)

  await expect(page.getByRole('link', { name: /Technician/ })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'My jobs' })).toHaveCount(0)

  await page.goto('/workers')
  await expect(page.getByText('Not available for your role')).toBeVisible()
})

test('an unauthenticated visitor is sent to sign in', async ({ page }) => {
  await page.goto('/tickets')
  await expect(page).toHaveURL(/\/login/)
})

test('a deep link is remembered, but only until someone signs out', async ({ page }) => {
  await signIn(page, SEEDED.dispatcher)
  const ticket = page.getByRole('link', { name: /trapped|ELV-/i }).first()
  await ticket.click()
  const ticketUrl = page.url()

  await test.step('an expired session returns you to where you were', async () => {
    await page.evaluate(() => localStorage.clear())
    await page.goto(ticketUrl)
    await expect(page).toHaveURL(/\/login/)

    await page.getByLabel('Email').fill(SEEDED.dispatcher.email)
    await page.getByLabel('Password').fill(SEEDED.dispatcher.password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page).toHaveURL(ticketUrl)
  })

  await test.step('signing out does not hand that page to the next person', async () => {
    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page).toHaveURL(/\/login/)

    await page.getByLabel('Email').fill(SEEDED.reporter.email)
    await page.getByLabel('Password').fill(SEEDED.reporter.password)
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page).toHaveURL(/\/tickets$/)
    await expect(page.getByRole('heading', { name: 'Incidents' })).toBeVisible()
  })
})
