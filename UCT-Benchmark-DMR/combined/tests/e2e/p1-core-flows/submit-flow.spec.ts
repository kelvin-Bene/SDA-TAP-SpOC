import { test, expect } from '../fixtures/consoleWatcher';
import * as path from 'path';

test.describe('P1 Core — Submit flow', () => {
  test('submit page loads with dropzone and form', async ({ page }) => {
    await page.goto('/submit');
    await expect(page.getByRole('heading', { name: /Submit Algorithm Results/i })).toBeVisible();
    await expect(page.getByText(/Drag & drop your submission file here/i)).toBeVisible();
    await expect(page.getByRole('heading', { name: /Submission Details/i })).toBeVisible();
  });

  test('valid JSON upload passes all 5 validation steps', async ({ page }) => {
    await page.goto('/submit');
    const fixturePath = path.resolve(__dirname, '..', 'fixtures', 'valid_submission.json');

    // Target the dropzone by its unique text; the Sample UCTP card now sits above
    // the upload area so index-based selectors don't resolve to the dropzone anymore.
    const dropzone = page
      .getByText(/Drag & drop your submission file here/i)
      .locator('..')
      .locator('..');

    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      dropzone.click(),
    ]);
    await fileChooser.setFiles(fixturePath);

    // All 5 validation rows become "passed"
    await expect(page.getByText('File format (valid JSON)').locator('..').getByText('passed')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('UCTP schema').locator('..').getByText('passed')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Observation ID references').locator('..').getByText('passed')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('State vector').locator('..').getByText('passed')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Covariance format').locator('..').getByText('passed')).toBeVisible({ timeout: 5000 });
  });

  test('target dataset dropdown populates from API', async ({ page }) => {
    await page.goto('/submit');
    await page.getByRole('combobox').filter({ hasText: /Select a dataset/i }).click();
    // At least one option visible
    await expect(page.getByRole('option').first()).toBeVisible();
  });
});
