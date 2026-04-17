import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P0 Smoke — App loads', () => {
  test('root redirects to /dashboard when auto-logged in', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page).toHaveTitle(/UCT Benchmark/);
  });

  test('root shows landing when demo_logged_out flag is set', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('demo_logged_out', 'true');
    });
    await page.goto('/');
    await expect(page.getByRole('button', { name: /Try Demo/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Go to Main/i }).first()).toBeVisible();
  });

  test('header + sidebar render on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Toggle menu' })).toBeVisible();
    await expect(page.getByRole('link', { name: /Dashboard/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /Datasets/ }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Submit/ }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Leaderboard/ }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Docs/ }).first()).toBeVisible();
  });

  test('sidebar nav reaches every top-level route', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: /^Datasets$/ }).first().click();
    await expect(page).toHaveURL(/\/datasets$/);

    await page.getByRole('link', { name: /^Submit$/ }).first().click();
    await expect(page).toHaveURL(/\/submit$/);

    await page.getByRole('link', { name: /^Leaderboard$/ }).first().click();
    await expect(page).toHaveURL(/\/leaderboard$/);

    await page.getByRole('link', { name: /^Docs$/ }).first().click();
    await expect(page).toHaveURL(/\/docs$/);
  });

  test('favicon and index.html serve 200', async ({ page }) => {
    const root = await page.request.get('/');
    expect(root.status()).toBe(200);
  });
});
