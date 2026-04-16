import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for the UCT Benchmark frontend.
 *
 * Four projects cover mobile / tablet / desktop viewports:
 *   - mobile-safari: iPhone SE (375×667) with WebKit + touch
 *   - mobile-chrome: Pixel 5 (393×851) with Chromium + touch
 *   - tablet:        iPad (gen 7) (810×1080) with WebKit + touch
 *   - desktop:       Chromium 1280×800 (no touch)
 *
 * Use `devices[...]` profiles over raw `viewport` so `hasTouch`, `isMobile`,
 * UA, and device pixel ratio are all set correctly — the `touch:` Tailwind
 * variant and any `useBreakpoint` / touch feature-detects rely on these.
 *
 * To run against a deployed URL (e.g. Railway prod):
 *   PLAYWRIGHT_BASE_URL=https://frontend-production-6d80.up.railway.app npx playwright test
 * When PLAYWRIGHT_BASE_URL is set, the local dev webServer is skipped.
 */
const EXTERNAL_BASE_URL = process.env.PLAYWRIGHT_BASE_URL;
const BASE_URL = EXTERNAL_BASE_URL || 'http://localhost:3000';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  // Only start the local dev server when we're pointing at localhost.
  webServer: EXTERNAL_BASE_URL
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  projects: [
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone SE'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'tablet',
      use: { ...devices['iPad (gen 7)'] },
    },
    {
      name: 'desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
      },
    },
  ],
});
