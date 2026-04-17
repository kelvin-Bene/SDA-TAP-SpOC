import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas } from '../helpers/cesium';

test.describe('P1 Core — Dataset detail', () => {
  test('detail page shows name, stats, and Cesium canvas', async ({ page }) => {
    await page.goto('/datasets/1');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByText('Objects').first()).toBeVisible();
    await expect(page.getByText('Observations').first()).toBeVisible();
    await expect(page.getByText('Coverage').first()).toBeVisible();
    await waitForCesiumCanvas(page);
  });

  test('dataset information section renders', async ({ page }) => {
    await page.goto('/datasets/1');
    await expect(page.getByRole('heading', { name: /Dataset Information/i })).toBeVisible();
    await expect(page.getByText('Created').first()).toBeVisible();
    await expect(page.getByText('Regime').first()).toBeVisible();
    await expect(page.getByText('Tier').first()).toBeVisible();
  });

  test('observations sample table renders', async ({ page }) => {
    await page.goto('/datasets/1');
    // Wait for main content observations heading + table to load
    await expect(page.getByRole('heading', { name: 'Observations (Sample)' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Showing \d+ of [\d,]+ observations/i)).toBeVisible();
  });
});
