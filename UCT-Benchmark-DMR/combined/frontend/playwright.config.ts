import { defineConfig, devices } from '@playwright/test';
import { config as loadDotenv } from 'dotenv';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Playwright configuration for the UCT Benchmark frontend.
 *
 * Two test surfaces:
 *
 *   1. Dev-scope (default) — four projects (mobile-safari, mobile-chrome,
 *      tablet, desktop) that run the existing e2e/*.spec.ts against a local
 *      dev server with auth disabled (VITE_AUTH_ENABLED=false).
 *
 *   2. Prod-scope (opt-in) — two projects (desktop-auth, mobile-safari-auth)
 *      that run e2e/prod/*.spec.ts against a real deployed URL with a real
 *      Supabase session. Depends on the `setup` project which logs in once
 *      via auth.setup.ts and saves storageState to e2e/.auth/user.json.
 *
 * Run dev-scope (local):
 *   npx playwright test
 *
 * Run prod-scope (against Railway):
 *   npm run test:e2e:prod
 */

// Load frontend/.env.local (gitignored) for PLAYWRIGHT_TEST_EMAIL / PASSWORD /
// BASE_URL / API_URL. Does nothing if the file is absent.
loadDotenv({ path: path.resolve(__dirname, '.env.local') });

const EXTERNAL_BASE_URL = process.env.PLAYWRIGHT_BASE_URL;
const BASE_URL = EXTERNAL_BASE_URL || 'http://localhost:3000';
const STORAGE_STATE = path.resolve(__dirname, 'e2e/.auth/user.json');

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
    // Dev-scope projects (run existing e2e/*.spec.ts, skip e2e/prod/**).
    {
      name: 'mobile-safari',
      testIgnore: /prod\//,
      use: { ...devices['iPhone SE'], viewport: { width: 375, height: 667 } },
    },
    {
      name: 'mobile-chrome',
      testIgnore: /prod\//,
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'tablet',
      testIgnore: /prod\//,
      use: { ...devices['iPad (gen 7)'] },
    },
    {
      name: 'desktop',
      testIgnore: /prod\//,
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
      },
    },

    // Prod-scope — logs in once, stores session for auth projects.
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },

    // Prod-scope — desktop authenticated specs (most of the prod suite).
    // Flakes under parallel workers are common against cold-started prod,
    // so give every prod test a single retry even outside CI.
    {
      name: 'desktop-auth',
      dependencies: ['setup'],
      testMatch: /prod\/.*\.spec\.ts/,
      testIgnore: /prod\/90-mobile-parity/,
      retries: process.env.CI ? 2 : 1,
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
        storageState: STORAGE_STATE,
      },
    },

    // Prod-scope — iPhone SE authenticated specs (mobile overhaul regression).
    {
      name: 'mobile-safari-auth',
      dependencies: ['setup'],
      testMatch: /prod\/(00-public|90-mobile-parity|10-dashboard|20-datasets-browse|30-submit-filter|40-results-composite|50-leaderboard)\.spec\.ts/,
      retries: process.env.CI ? 2 : 1,
      use: {
        ...devices['iPhone SE'],
        viewport: { width: 375, height: 667 },
        storageState: STORAGE_STATE,
      },
    },
  ],
});
