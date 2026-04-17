import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Docs all tabs deep', () => {
  test('Getting Started tab has welcome + orbital regime legend', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.getByText('Welcome to UCT Benchmark')).toBeVisible();
    await expect(page.getByText('Quick Start Steps')).toBeVisible();
    await expect(page.getByText('Orbital Regimes')).toBeVisible();
    await expect(page.getByText('Data Tiers')).toBeVisible();
  });

  test('Dataset Format tab has code block', async ({ page }) => {
    await page.goto('/docs');
    await page.getByRole('tab', { name: 'Dataset Format' }).click();
    await expect(page.getByRole('heading', { name: /Dataset Format Specification/i })).toBeVisible();
    // Code block (<pre> or <code>) present
    const codeCount = await page.locator('pre, code').count();
    expect(codeCount).toBeGreaterThan(0);
  });

  test('Submission Format tab has code block', async ({ page }) => {
    await page.goto('/docs');
    await page.getByRole('tab', { name: 'Submission Format' }).click();
    await expect(page.getByRole('heading', { name: /Submission Format Specification/i })).toBeVisible();
    const codeCount = await page.locator('pre, code').count();
    expect(codeCount).toBeGreaterThan(0);
  });

  test('Evaluation Metrics tab', async ({ page }) => {
    await page.goto('/docs');
    await page.getByRole('tab', { name: 'Evaluation Metrics' }).click();
    await expect(page.getByRole('heading', { name: /Evaluation Metrics/i })).toBeVisible();
  });

  test('Pipeline tab', async ({ page }) => {
    await page.goto('/docs');
    await page.getByRole('tab', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: /Processing Pipeline/i })).toBeVisible();
  });
});
