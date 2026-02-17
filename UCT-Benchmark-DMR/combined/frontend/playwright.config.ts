import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for SpOC Benchmark Platform E2E tests.
 *
 * Requires running services:
 * - Backend API on port 8000
 * - Frontend dev server on port 3000
 * - Supabase on port 54321 (for auth-enabled tests)
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ['json', { outputFile: 'e2e-results.json' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'public',
      testMatch: /\/(landing-page|login-page)\.spec\.ts$/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'chromium',
      testIgnore: /\/(landing-page|login-page)\.spec\.ts$/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  /* Expect services to already be running */
  expect: {
    timeout: 10000,
  },
  timeout: 30000,
});
