import { defineConfig, devices } from '@playwright/test'


export default defineConfig({
  testDir: './browser_tests/tests',
  testMatch: /customWorkflowRoundtrip\.spec\.ts/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  reporter: 'line',
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_URL || 'http://127.0.0.1:8188',
    trace: 'on-first-retry'
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome']
      },
      timeout: 15000
    }
  ]
})
