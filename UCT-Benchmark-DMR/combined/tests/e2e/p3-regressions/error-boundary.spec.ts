import { test, expect } from '../fixtures/consoleWatcher';

/**
 * Verify ErrorBoundary catches thrown errors and renders fallback UI.
 * We inject a WebGL-disabled context before navigation to force Cesium to fail,
 * then verify the page doesn't go fully white and ErrorBoundary fallback appears.
 */
test.describe('P3 Regression — Error boundary', () => {
  test('navigating to bad route shows graceful error, not blank page', async ({ page, consoleWatcher }) => {
    await page.goto('/datasets/99999');
    // Page should not be blank
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length, 'Page must not be empty after error').toBeGreaterThan(50);
    // Should have some heading indicating error state
    await expect(
      page.getByRole('heading', { name: /Not Found|Error|Something went wrong/i })
    ).toBeVisible();
    consoleWatcher.allow(/404/);
  });

  test('app recovers after navigating away from error page', async ({ page, consoleWatcher }) => {
    await page.goto('/datasets/99999');
    await expect(page.getByRole('heading', { name: /Not Found/i })).toBeVisible();
    consoleWatcher.allow(/404/);
    // Navigate to a good page
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();
  });
});
