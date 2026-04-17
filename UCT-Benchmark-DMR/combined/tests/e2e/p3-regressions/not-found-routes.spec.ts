import { test, expect } from '../fixtures/consoleWatcher';

/**
 * Guards the catch-all router and graceful-error pages for invalid IDs.
 */
test.describe('P3 Regression — Not-found routes', () => {
  test('unknown route shows NotFoundPage with Go Home', async ({ page }) => {
    await page.goto('/definitely-missing-route-abc-xyz');
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
    await expect(page.getByText(/Page Not Found/i)).toBeVisible();
    await expect(page.getByRole('link', { name: /Go Home/i })).toBeVisible();
  });

  test('Go Home button returns to dashboard', async ({ page }) => {
    await page.goto('/no-such-page');
    await page.getByRole('link', { name: /Go Home/i }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test('bad dataset ID shows Dataset Not Found', async ({ page, consoleWatcher }) => {
    await page.goto('/datasets/99999');
    await expect(page.getByRole('heading', { name: /Dataset Not Found/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Browse Datasets/i })).toBeVisible();
    // Allow expected 404 API errors
    consoleWatcher.allow(/404/);
  });

  test('bad submission ID shows Submission Not Found', async ({ page, consoleWatcher }) => {
    await page.goto('/results/99999');
    await expect(page.getByRole('heading', { name: /Submission Not Found/i })).toBeVisible();
    consoleWatcher.allow(/404/);
  });
});
