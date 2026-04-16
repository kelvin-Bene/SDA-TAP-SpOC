/**
 * Auth setup — runs once as a dependency of the *-auth projects.
 *
 * Logs into the production Supabase auth flow via the real LoginPage UI,
 * waits for redirect to /dashboard, then persists the browser's storage
 * state (cookies + localStorage, including the Supabase session JWT) to
 * e2e/.auth/user.json. Subsequent authenticated specs load that state via
 * `use.storageState` and skip the login UI entirely.
 *
 * Env:
 *   PLAYWRIGHT_TEST_EMAIL     — kelvin@thebenedicts.net (or any owner)
 *   PLAYWRIGHT_TEST_PASSWORD  — corresponding password
 *   PLAYWRIGHT_BASE_URL       — set by the config; defaults to prod
 *
 * If email/password are absent, the setup is skipped with a loud warning
 * and auth-gated specs will fail to find the storageState — which is the
 * intended signal.
 */
import { test as setup, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_FILE = path.resolve(__dirname, '.auth/user.json');

setup('authenticate against prod', async ({ page }) => {
  const email = process.env.PLAYWRIGHT_TEST_EMAIL;
  const password = process.env.PLAYWRIGHT_TEST_PASSWORD;

  if (!email || !password) {
    throw new Error(
      'PLAYWRIGHT_TEST_EMAIL and PLAYWRIGHT_TEST_PASSWORD must be set in ' +
        'frontend/.env.local (gitignored). See .env.local.example for the template.'
    );
  }

  await page.goto('/login');

  // The LoginPage renders email + password inputs + a "Sign In" submit.
  // Matches frontend/src/pages/LoginPage.tsx (password-based Supabase
  // signInWithPassword at authStore.ts:123).
  const emailInput = page.getByRole('textbox', { name: /email/i }).first();
  const passwordInput = page.locator('input[type="password"]').first();

  await expect(emailInput).toBeVisible({ timeout: 15_000 });
  await emailInput.fill(email);
  await passwordInput.fill(password);

  // Submit via the button. Matches the disabled-on-load-state pattern so
  // we click after fields are filled (button enables when both have value).
  const submit = page.getByRole('button', { name: /^sign in$/i }).first();
  await submit.click();

  // Success = redirect to /dashboard (the authenticated landing).
  // Some cold-starts take a beat; give it a generous window.
  await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
  await expect(page.locator('main')).toBeVisible();

  // Persist storage state (cookies + localStorage) to disk.
  await page.context().storageState({ path: AUTH_FILE });
});
