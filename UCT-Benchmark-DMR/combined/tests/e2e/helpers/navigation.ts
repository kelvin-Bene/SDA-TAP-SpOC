import { expect, type Page } from '@playwright/test';

/** Navigate and wait for the page heading to be visible (handles Suspense). */
export async function gotoAndHydrate(
  page: Page,
  path: string,
  opts: { headingText?: string | RegExp; timeout?: number } = {},
): Promise<void> {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  if (opts.headingText) {
    await expect(page.locator('h1')).toContainText(opts.headingText, { timeout: opts.timeout ?? 15_000 });
  } else {
    await page.waitForLoadState('domcontentloaded');
  }
}

/** Verify demo mode invariants: no auth redirect, no supabase cookies. */
export async function assertNoAuthState(page: Page): Promise<void> {
  const state = await page.evaluate(() => ({
    url: window.location.href,
    lsAuth: Object.keys(localStorage).filter((k) => /supabase|auth|session|token/i.test(k)),
    ssAuth: Object.keys(sessionStorage).filter((k) => /supabase|auth|session|token/i.test(k)),
    cookieAuth: document.cookie.split(';').filter((c) => /supabase|auth/i.test(c)),
  }));
  expect(state.url, 'URL must not redirect to login').not.toMatch(/\/login|\/welcome|\/signin/);
  expect(state.lsAuth, 'localStorage must not hold auth tokens in demo').toEqual([]);
  expect(state.ssAuth, 'sessionStorage must not hold auth tokens in demo').toEqual([]);
}
