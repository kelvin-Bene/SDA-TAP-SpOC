import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Results export flows', () => {
  const SUBMISSION_ID = 8;

  test('CSV export downloads real file with correct extension', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'CSV' }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/results.*\.csv$/);
  });

  test('JSON export downloads real file with correct extension', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Export JSON' }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/results.*\.json$/);
  });

  test('PDF Download Report produces PDF', async ({ page }) => {
    await page.goto(`/results/${SUBMISSION_ID}`);
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /Download Report/i }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/report.*\.pdf$/);
  });
});
