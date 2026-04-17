import { test, expect } from '../fixtures/consoleWatcher';
import { assertNoAuthState } from '../helpers/navigation';

test.describe('P0 Smoke — Demo auto-login', () => {
  test('dashboard shows Demo User greeting without login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();
    await expect(page).not.toHaveURL(/\/login|\/welcome|\/signin/);
  });

  test('no Supabase auth requests fired', async ({ page }) => {
    const supabaseRequests: string[] = [];
    page.on('request', (req) => {
      if (/supabase\.co/.test(req.url())) supabaseRequests.push(req.url());
    });
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    expect(supabaseRequests, 'Demo mode must not call supabase').toEqual([]);
  });

  test('no auth state in storage or cookies after navigation', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
    await assertNoAuthState(page);
  });
});
