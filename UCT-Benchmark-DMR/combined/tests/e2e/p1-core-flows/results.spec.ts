import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P1 Core — Results page', () => {
  test('results page shows metadata header and 4 StatCards', async ({ page }) => {
    await page.goto('/results/8');
    // Allow longer for initial API fetch on Railway
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText('F1-Score').first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Precision').first()).toBeVisible();
    await expect(page.getByText('Recall').first()).toBeVisible();
    await expect(page.getByText('Rank').first()).toBeVisible();
  });

  test('all 4 result tabs render', async ({ page }) => {
    await page.goto('/results/8');
    await expect(page.getByRole('tab', { name: 'Binary Metrics' })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole('tab', { name: 'State Metrics' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Residual Analysis' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Per-Satellite' })).toBeVisible();
  });

  test('state metrics tab shows RMS numbers', async ({ page }) => {
    await page.goto('/results/8');
    await page.getByRole('tab', { name: 'State Metrics' }).click();
    await expect(page.getByText(/Position RMS/i)).toBeVisible();
    await expect(page.getByText(/Velocity RMS/i)).toBeVisible();
  });

  test('residuals tab shows RA and Dec histograms', async ({ page }) => {
    await page.goto('/results/8');
    await page.getByRole('tab', { name: 'Residual Analysis' }).click();
    await expect(page.getByRole('heading', { name: /RA Residuals/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Dec Residuals/i })).toBeVisible();
  });

  test('per-satellite tab shows breakdown table', async ({ page }) => {
    await page.goto('/results/8');
    await page.getByRole('tab', { name: 'Per-Satellite' }).click();
    await expect(page.getByRole('heading', { name: /Per-Satellite Breakdown/i })).toBeVisible();
    await expect(page.getByText(/Satellite ID/i)).toBeVisible();
  });

  test('CSV export triggers download', async ({ page }) => {
    await page.goto('/results/8');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'CSV' }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.csv$/);
  });

  test('JSON export triggers download', async ({ page }) => {
    await page.goto('/results/8');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Export JSON' }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.json$/);
  });

  test('Download Report triggers PDF download', async ({ page }) => {
    await page.goto('/results/8');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /Download Report/i }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  });
});
