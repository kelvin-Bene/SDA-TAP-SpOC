import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P1 Core — Datasets browse', () => {
  test('dataset cards render with metadata', async ({ page }) => {
    await page.goto('/datasets');
    await expect(page.getByRole('heading', { name: 'Datasets', level: 1 })).toBeVisible();
    await expect(page.getByText(/Showing \d+ datasets/i)).toBeVisible();
    // At least one card
    await expect(page.locator('a[href^="/datasets/"]').first()).toBeVisible();
  });

  test('filters: regime dropdown narrows results', async ({ page }) => {
    await page.goto('/datasets');
    await expect(page.getByText(/Showing \d+ datasets/i)).toBeVisible();
    const initialText = await page.getByText(/Showing \d+ datasets/i).textContent();
    const initial = Number(initialText?.match(/\d+/)?.[0]);

    // Open regime combobox, select MEO
    await page.getByRole('combobox').filter({ hasText: /All Regimes/i }).click();
    await page.getByRole('option', { name: /MEO/i }).click();

    await page.waitForTimeout(500);
    const filteredText = await page.getByText(/Showing \d+ datasets/i).textContent();
    const filtered = Number(filteredText?.match(/\d+/)?.[0]);
    expect(filtered).toBeLessThanOrEqual(initial);
  });

  test('grid / list view toggle', async ({ page }) => {
    await page.goto('/datasets');
    await page.getByRole('button', { name: 'List view' }).click();
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Grid view' }).click();
    await page.waitForTimeout(300);
  });

  test('preview dialog opens with 3 tabs', async ({ page }) => {
    await page.goto('/datasets');
    await page.getByRole('button', { name: 'Preview dataset' }).first().click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Overview' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Statistics' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Sample Data' })).toBeVisible();

    await page.getByRole('tab', { name: 'Sample Data' }).click();
    // Sample data tab shows JSON
    await expect(page.getByRole('dialog')).toContainText(/obsId|ra|dec/i);
  });
});
