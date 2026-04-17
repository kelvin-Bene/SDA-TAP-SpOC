import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Dataset preview dialog tabs', () => {
  test('Overview tab shows metadata', async ({ page }) => {
    await page.goto('/datasets');
    await page.getByRole('button', { name: 'Preview dataset' }).first().click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Overview' })).toHaveAttribute('data-state', 'active');
  });

  test('Statistics tab shows chart/stats', async ({ page }) => {
    await page.goto('/datasets');
    await page.getByRole('button', { name: 'Preview dataset' }).first().click();
    await page.getByRole('tab', { name: 'Statistics' }).click();
    await expect(page.getByRole('tab', { name: 'Statistics' })).toHaveAttribute('data-state', 'active');
  });

  test('Sample Data tab shows JSON', async ({ page }) => {
    await page.goto('/datasets');
    await page.getByRole('button', { name: 'Preview dataset' }).first().click();
    await page.getByRole('tab', { name: 'Sample Data' }).click();
    await expect(page.getByRole('dialog')).toContainText(/obsId|observations|time|ra/i);
  });

  test('dialog has Download Dataset action', async ({ page }) => {
    await page.goto('/datasets');
    await page.getByRole('button', { name: 'Preview dataset' }).first().click();
    await expect(page.getByRole('button', { name: /Download Dataset/i })).toBeVisible();
  });

  test('dialog closes via close button', async ({ page }) => {
    await page.goto('/datasets');
    await page.getByRole('button', { name: 'Preview dataset' }).first().click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Close' }).first().click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
});
