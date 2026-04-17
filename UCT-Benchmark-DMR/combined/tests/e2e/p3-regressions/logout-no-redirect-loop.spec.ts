import { test, expect } from '../fixtures/consoleWatcher';

/**
 * Regression guard for the specific logout bug: before the fix, clicking Log out
 * navigated to /login which redirected to /dashboard which AuthGuard kicked back
 * to /dashboard — an infinite redirect loop / blank screen.
 * Now demo logout should redirect externally to the unified prod landing URL
 * in exactly one hop.
 */
const PROD_LANDING = /^https:\/\/frontend-production-6d80\.up\.railway\.app\//;

test.describe('P3 Regression — Logout produces no redirect loop', () => {
  test('logout click produces one navigation to production landing', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();

    const navigations: string[] = [];
    page.on('framenavigated', (frame) => {
      if (frame === page.mainFrame()) {
        navigations.push(frame.url());
      }
    });

    const navigationPromise = page.waitForRequest(
      /frontend-production-6d80\.up\.railway\.app/,
      { timeout: 10_000 },
    );
    await page.getByRole('button', { name: 'User menu' }).click();
    await page.getByRole('menuitem', { name: /Log out/i }).click();
    const req = await navigationPromise;
    expect(req.url()).toMatch(PROD_LANDING);

    // A loop would produce many more navigations — cap at a small number.
    expect(
      navigations.length,
      `Unexpected navigations: ${navigations.join(' -> ')}`,
    ).toBeLessThanOrEqual(3);
  });

  test('no supabase.co requests during logout click in demo mode', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();

    const supabaseHits: string[] = [];
    page.on('request', (req) => {
      if (/supabase\.co/.test(req.url())) supabaseHits.push(req.url());
    });

    const navigationPromise = page.waitForRequest(
      /frontend-production-6d80\.up\.railway\.app/,
      { timeout: 10_000 },
    );
    await page.getByRole('button', { name: 'User menu' }).click();
    await page.getByRole('menuitem', { name: /Log out/i }).click();
    await navigationPromise;
    expect(supabaseHits).toEqual([]);
  });
});
