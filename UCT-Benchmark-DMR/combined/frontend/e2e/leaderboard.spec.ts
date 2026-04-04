import { test, expect } from './fixtures';

test.describe('Leaderboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/leaderboard');
    await page.waitForLoadState('domcontentloaded');
  });

  test('leaderboard renders with heading', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /leaderboard/i }).first();
    await expect(heading).toBeVisible();
  });

  test('leaderboard shows table or card layout', async ({ page }) => {
    const table = page.locator('table, [class*="card"], [role="table"]').first();
    await expect(table).toBeVisible({ timeout: 5000 });
  });

  test('regime filter is visible', async ({ page }) => {
    // Use label selector to avoid strict mode with label + combobox both matching
    const filter = page.locator('label').filter({ hasText: /regime/i }).first();
    await expect(filter).toBeVisible({ timeout: 5000 });
  });

  test('tier filter is visible', async ({ page }) => {
    const filter = page.locator('label').filter({ hasText: /tier/i }).first();
    await expect(filter).toBeVisible({ timeout: 5000 });
  });

  test('period filter is visible', async ({ page }) => {
    const filter = page.locator('text=/all time|month|week|period/i').first();
    await expect(filter).toBeVisible({ timeout: 5000 });
  });

  test('handles empty leaderboard state', async ({ page }) => {
    // Even with no data, page should render without errors
    const content = page.locator('text=/no entries|no submissions|leaderboard/i').first()
      .or(page.locator('table, [class*="empty"]').first());
    await expect(content).toBeVisible({ timeout: 5000 });
  });

  test('page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/leaderboard');
    await page.waitForTimeout(3000);
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('.map') && !e.includes('404') && !e.includes('ERR_CONNECTION')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
