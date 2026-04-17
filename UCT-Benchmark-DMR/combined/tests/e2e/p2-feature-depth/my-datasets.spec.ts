import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — My Datasets', () => {
  test('my datasets page loads with stats', async ({ page }) => {
    await page.goto('/datasets/my-datasets');
    await expect(page.getByRole('heading', { name: 'My Datasets', level: 1 })).toBeVisible();
    await expect(page.getByText(/Total Datasets/i)).toBeVisible();
    await expect(page.getByText(/Total Objects/i)).toBeVisible();
    await expect(page.getByText(/Storage Used/i)).toBeVisible();
  });

  test('Your Datasets table has rows with required columns', async ({ page }) => {
    await page.goto('/datasets/my-datasets');
    await expect(page.getByRole('heading', { name: /Your Datasets/i })).toBeVisible();
    await expect(page.getByText('Name').first()).toBeVisible();
    await expect(page.getByText('Status').first()).toBeVisible();
    await expect(page.getByText('Version').first()).toBeVisible();
    await expect(page.getByText('Regime').first()).toBeVisible();
    await expect(page.getByText('Tier').first()).toBeVisible();
  });

  test('Generate New button navigates to generate page', async ({ page }) => {
    await page.goto('/datasets/my-datasets');
    await page.getByRole('main').getByRole('link', { name: /Generate New/i }).click();
    await expect(page).toHaveURL(/\/datasets\/generate$/);
  });
});
