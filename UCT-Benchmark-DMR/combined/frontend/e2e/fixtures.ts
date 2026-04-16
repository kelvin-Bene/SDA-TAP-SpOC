import { test as base, expect, Page, TestInfo } from '@playwright/test';

/**
 * Shared fixtures and helpers for E2E tests.
 *
 * Auth mode: Tests run against VITE_AUTH_ENABLED=false (default),
 * so protected routes are accessible without login.
 *
 * Projects (see playwright.config.ts):
 *   - mobile-safari (iPhone SE 375×667)
 *   - mobile-chrome (Pixel 5 393×851)
 *   - tablet (iPad gen 7)
 *   - desktop (1280×800)
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

/** True when the current test project is one of the mobile viewport projects. */
export function isMobile(testInfo: TestInfo): boolean {
  return testInfo.project.name.startsWith('mobile');
}

/** True when the current test project is the tablet project. */
export function isTablet(testInfo: TestInfo): boolean {
  return testInfo.project.name === 'tablet';
}

/** True when the current test project is the desktop project. */
export function isDesktop(testInfo: TestInfo): boolean {
  return testInfo.project.name === 'desktop';
}

/**
 * Open the sidebar drawer (visible on <lg: viewports via Header menu button).
 * No-op on desktop where the sidebar is pinned open via `lg:ml-72`.
 */
export async function openMobileMenu(page: Page) {
  const menuButton = page.getByRole('button', { name: /toggle menu/i });
  await menuButton.click();
  // Wait for the sidebar <aside> to slide in (aria-hidden flips to false)
  await page.locator('aside[aria-hidden="false"]').waitFor({ state: 'visible' });
}

/**
 * Assert that the page has no horizontal scrolling at the current viewport.
 * A bottom-line mobile guarantee — the body should never be wider than the viewport.
 */
export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(
    overflow.scrollWidth,
    `page document (${overflow.scrollWidth}px) should not be wider than viewport (${overflow.innerWidth}px)`,
  ).toBeLessThanOrEqual(overflow.innerWidth);
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
