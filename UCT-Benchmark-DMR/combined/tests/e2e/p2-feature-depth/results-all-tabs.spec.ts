import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Results page all tabs deep', () => {
  const SUBMISSION_ID = 8;

  test('Binary Metrics tab shows confusion matrix + classification bars', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    await expect(page.getByRole('heading', { name: /Confusion Matrix/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Classification Metrics/i })).toBeVisible();
    await expect(page.getByText(/True Positive/i)).toBeVisible();
    await expect(page.getByText(/False Negative/i)).toBeVisible();
    await expect(page.getByText(/False Positive/i)).toBeVisible();
    await expect(page.getByText(/True Negative/i)).toBeVisible();
  });

  test('State Metrics tab shows RMS + histogram', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    await page.getByRole('tab', { name: 'State Metrics' }).click();
    await expect(page.getByRole('heading', { name: /State Vector Accuracy/i })).toBeVisible();
    await expect(page.getByText(/Position RMS/i)).toBeVisible();
    await expect(page.getByText(/Velocity RMS/i)).toBeVisible();
    await expect(page.getByText(/Mahalanobis Distance/i)).toBeVisible();
    await expect(page.getByRole('heading', { name: /Position Error Distribution/i })).toBeVisible();
  });

  test('Residual Analysis tab shows RA and Dec histograms with RMS values', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    await page.getByRole('tab', { name: 'Residual Analysis' }).click();
    await expect(page.getByRole('heading', { name: /RA Residuals/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Dec Residuals/i })).toBeVisible();
    await expect(page.getByText(/RMS: \d+\.\d+ arcsec/i).first()).toBeVisible();
  });

  test('Per-Satellite tab shows table with required columns', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    await page.getByRole('tab', { name: 'Per-Satellite' }).click();
    await expect(page.getByText('Satellite ID').first()).toBeVisible();
    await expect(page.getByText('Status').first()).toBeVisible();
    await expect(page.getByText('Obs Used').first()).toBeVisible();
    await expect(page.getByText('Pos Error').first()).toBeVisible();
    await expect(page.getByText('Vel Error').first()).toBeVisible();
    await expect(page.getByText('Confidence').first()).toBeVisible();
  });

  test('Per-Satellite shows "Showing N of M satellites"', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    await page.getByRole('tab', { name: 'Per-Satellite' }).click();
    await expect(page.getByText(/Showing \d+ of \d+ satellites/i)).toBeVisible();
  });
});
