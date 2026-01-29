import { test as base, expect, Page } from '@playwright/test';

/**
 * Shared fixtures and helpers for E2E tests.
 *
 * Auth mode: Tests run against VITE_AUTH_ENABLED=false (default),
 * so protected routes are accessible without login.
 */

/** Wait for the page to finish loading (no pending network requests). */
async function waitForPageReady(page: Page) {
  await page.waitForLoadState('domcontentloaded');
}

/** Navigate and wait for the page to be ready. */
async function navigateAndWait(page: Page, path: string) {
  await page.goto(path);
  await waitForPageReady(page);
}

/** Wait for an API response on a given URL pattern. */
async function waitForAPI(page: Page, urlPattern: string | RegExp) {
  return page.waitForResponse(
    (resp) =>
      (typeof urlPattern === 'string'
        ? resp.url().includes(urlPattern)
        : urlPattern.test(resp.url())) && resp.status() < 400
  );
}

export const test = base.extend<{
  navigateAndWait: (path: string) => Promise<void>;
  waitForAPI: (pattern: string | RegExp) => Promise<import('@playwright/test').Response>;
}>({
  navigateAndWait: async ({ page }, use) => {
    await use((path: string) => navigateAndWait(page, path));
  },
  waitForAPI: async ({ page }, use) => {
    await use((pattern: string | RegExp) => waitForAPI(page, pattern));
  },
});

export { expect };
