import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  // The workflow test hands one ticket between four roles in order, so the steps
  // cannot be parallelised or retried halfway through. Four sign-ins and a dozen
  // round trips do not fit in the default 30s budget either.
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  // The screenshot pass documents the UI rather than checking it.
  grepInvert: /@screens/,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
