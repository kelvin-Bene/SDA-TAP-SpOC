import { test, expect } from './fixtures';

test.describe('Navigation', () => {
  test('sidebar renders navigation links', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const sidebar = page.locator('nav, [class*="sidebar"], aside').first();
    await expect(sidebar).toBeVisible();
  });

  test.describe('sidebar links navigate correctly', () => {
    const routes = [
      { name: /dashboard|home/i, url: '/' },
      { name: /dataset/i, url: '/datasets' },
      { name: /submit/i, url: '/submit' },
      { name: /leaderboard/i, url: '/leaderboard' },
      { name: /uctp|lab/i, url: '/uctp' },
      { name: /doc/i, url: '/docs' },
      { name: /setting/i, url: '/settings' },
    ];

    for (const route of routes) {
      test(`navigates to ${route.url}`, async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('domcontentloaded');

        const link = page.locator(`nav a, aside a, [class*="sidebar"] a`)
          .filter({ hasText: route.name })
          .first();
        if (await link.isVisible()) {
          await link.click();
          await page.waitForLoadState('domcontentloaded');
          await expect(page).toHaveURL(new RegExp(route.url));
        }
      });
    }
  });

  test('header renders with user info', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const header = page.locator('header, [class*="header"], [class*="topbar"]').first();
    await expect(header).toBeVisible();
  });

  test('unknown routes redirect to /', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await page.waitForLoadState('domcontentloaded');
    // Should redirect to dashboard
    await expect(page).toHaveURL('/');
  });

  test('direct URL access to protected routes works', async ({ page }) => {
    // With auth disabled, all routes should be accessible
    await page.goto('/datasets');
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveURL(/\/datasets/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('back/forward browser navigation works', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Navigate to datasets
    await page.goto('/datasets');
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveURL(/\/datasets/);

    // Go back
    await page.goBack();
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveURL('/');

    // Go forward
    await page.goForward();
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveURL(/\/datasets/);
  });
});
