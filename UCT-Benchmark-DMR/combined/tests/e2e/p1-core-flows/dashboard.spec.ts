import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas } from '../helpers/cesium';

test.describe('P1 Core — Dashboard', () => {
  test('4 StatCards render with data', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByText('Top Rank')).toBeVisible();
    await expect(page.getByText('Submissions').first()).toBeVisible();
    await expect(page.getByText('Best F1-Score')).toBeVisible();
    await expect(page.getByText('vs. Average')).toBeVisible();
  });

  test('Cesium 3D Orbit Visualization panel renders', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /3D Orbit Visualization/i })).toBeVisible();
    await waitForCesiumCanvas(page);
    await expect(page.getByText(/Showing \d+ satellites/i)).toBeVisible();
  });

  test('quick action CTAs navigate', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('main').getByRole('button', { name: 'Generate Dataset' }).click();
    await expect(page).toHaveURL(/\/datasets\/generate$/);

    await page.goto('/dashboard');
    await page.getByRole('main').getByRole('button', { name: 'Submit Algorithm' }).click();
    await expect(page).toHaveURL(/\/submit$/);
  });

  test('recent submissions links navigate to results', async ({ page }) => {
    await page.goto('/dashboard');
    // Target the main content's Recent Submissions (not sidebar Recent Results)
    const recentSubmissionsLinks = page.getByRole('main').locator('a[href^="/results/"]');
    await expect(recentSubmissionsLinks.first()).toBeVisible();
    const firstHref = await recentSubmissionsLinks.first().getAttribute('href');
    expect(firstHref).toMatch(/\/results\/\d+/);
  });
});
