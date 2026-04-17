import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P1 Core — My submissions', () => {
  test('my-submissions page loads with stats + table', async ({ page }) => {
    await page.goto('/submit/my-submissions');
    await expect(page.getByRole('heading', { name: /My Submissions/i })).toBeVisible();
    await expect(page.getByText('Total Submissions').first()).toBeVisible();
    await expect(page.getByText('Completed').first()).toBeVisible();
    await expect(page.getByText('Queued').first()).toBeVisible();
    await expect(page.getByText('Failed').first()).toBeVisible();
  });

  test('submission history table has rows', async ({ page }) => {
    await page.goto('/submit/my-submissions');
    await expect(page.getByRole('heading', { name: /Submission History/i })).toBeVisible();
    const rows = page.locator('table tbody tr');
    await expect.poll(() => rows.count(), { timeout: 10_000 }).toBeGreaterThan(0);
  });

  test('New Submission button navigates to /submit', async ({ page }) => {
    await page.goto('/submit/my-submissions');
    // Button in main content, not sidebar link
    await page.getByRole('main').getByRole('link', { name: /New Submission/i }).click();
    await expect(page).toHaveURL(/\/submit$/);
  });
});
