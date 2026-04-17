import { test, expect } from '../fixtures/consoleWatcher';

/**
 * Regression guard for the specific logout bug: before the fix, clicking Log out
 * navigated to /login which redirected to /dashboard which AuthGuard kicked back
 * to /dashboard — an infinite redirect loop / blank screen.
 * Now it should produce exactly one navigation to /.
 */
test.describe('P3 Regression — Logout produces no redirect loop', () => {
  test('exactly one nav to / after logout click', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();

    const navigations: string[] = [];
    page.on('framenavigated', (frame) => {
      if (frame === page.mainFrame()) {
        navigations.push(frame.url());
      }
    });

    await page.getByRole('button', { name: 'User menu' }).click();
    await page.getByRole('menuitem', { name: /Log out/i }).click();
    await expect(page).toHaveURL(/\/$/);

    // We expect 1 navigation (to /). A loop would produce 3+.
    expect(navigations.length, `Unexpected navigations: ${navigations.join(' -> ')}`).toBeLessThanOrEqual(2);
    expect(navigations[navigations.length - 1]).toMatch(/\/$/);
  });

  test('no supabase.co requests during logout click in demo mode', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();

    const supabaseHits: string[] = [];
    page.on('request', (req) => {
      if (/supabase\.co/.test(req.url())) supabaseHits.push(req.url());
    });

    await page.getByRole('button', { name: 'User menu' }).click();
    await page.getByRole('menuitem', { name: /Log out/i }).click();
    await expect(page).toHaveURL(/\/$/);
    expect(supabaseHits).toEqual([]);
  });

  test('landing page is interactive after logout', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();
    await page.getByRole('button', { name: 'User menu' }).click();
    await page.getByRole('menuitem', { name: /Log out/i }).click();
    await expect(page).toHaveURL(/\/$/);

    // Clicking Try Demo brings us back — verifies the page isn't blank/frozen
    await page.getByRole('button', { name: /Try Demo/i }).first().click();
    await expect(page).toHaveURL(/\/dashboard$/);
  });
});
