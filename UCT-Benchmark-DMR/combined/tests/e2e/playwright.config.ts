import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for UCT Benchmark E2E tests.
 *
 * Target: Railway live demo by default. Demo branch requires no auth / no API keys.
 * Override the target via FRONTEND_URL for localhost runs.
 */
const DEFAULT_BASE_URL = 'https://frontend-demo-1542.up.railway.app';

export default defineConfig({
  testDir: './',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 1,
  reporter: [
    ['html', { outputFolder: '../../playwright-report', open: 'never' }],
    ['json', { outputFile: '../../playwright-report/results.json' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.FRONTEND_URL || DEFAULT_BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    actionTimeout: 15_000,
    navigationTimeout: 60_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
