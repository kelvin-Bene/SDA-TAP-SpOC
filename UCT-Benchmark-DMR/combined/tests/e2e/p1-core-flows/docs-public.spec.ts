import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P1 Core — Docs public access', () => {
  test('docs page loads without auth', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.getByRole('heading', { name: 'Documentation', level: 1 })).toBeVisible();
    expect(page.url()).not.toMatch(/\/login|\/welcome/);
  });

  test('all 5 docs tabs exist', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.getByRole('tab', { name: 'Getting Started' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Dataset Format' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Submission Format' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Evaluation Metrics' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Pipeline' })).toBeVisible();
  });

  test('each docs tab switches content', async ({ page }) => {
    await page.goto('/docs');
    await page.getByRole('tab', { name: 'Dataset Format' }).click();
    await expect(page.getByRole('heading', { name: /Dataset Format Specification/i })).toBeVisible();

    await page.getByRole('tab', { name: 'Submission Format' }).click();
    await expect(page.getByRole('heading', { name: /Submission Format Specification/i })).toBeVisible();

    await page.getByRole('tab', { name: 'Evaluation Metrics' }).click();
    await expect(page.getByRole('heading', { name: /Evaluation Metrics/i })).toBeVisible();

    await page.getByRole('tab', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: /Processing Pipeline/i })).toBeVisible();
  });
});
