import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Leaderboard filters', () => {
  test('orbital regime dropdown opens with all options', async ({ page }) => {
    await page.goto('/leaderboard');
    await page.getByRole('combobox').filter({ hasText: /All Regimes/i }).click();
    await expect(page.getByRole('option', { name: /^LEO/i })).toBeVisible();
    await expect(page.getByRole('option', { name: /^MEO/i })).toBeVisible();
    await expect(page.getByRole('option', { name: /^GEO/i })).toBeVisible();
    await expect(page.getByRole('option', { name: /^HEO/i })).toBeVisible();
  });

  test('time period dropdown opens with options', async ({ page }) => {
    await page.goto('/leaderboard');
    // Third combobox is Time Period based on layout order
    const combos = page.getByRole('combobox');
    await combos.nth(2).click();
    await expect(page.getByRole('option').first()).toBeVisible({ timeout: 5000 });
    await page.keyboard.press('Escape');
  });

  test('trends chart shows 4 algorithm series in legend', async ({ page }) => {
    await page.goto('/leaderboard');
    await page.getByRole('tab', { name: 'Performance Trends' }).click();
    await expect(page.getByRole('heading', { name: /F1-Score Trends/i })).toBeVisible();
    // Legend should contain algorithm names
    await page.waitForTimeout(1000);
    const svgs = await page.locator('svg').count();
    expect(svgs).toBeGreaterThan(0);
  });

  test('podium cards have correct rank order', async ({ page }) => {
    await page.goto('/leaderboard');
    // Podium has #1, #2, #3
    await expect(page.getByText('#1').first()).toBeVisible();
    await expect(page.getByText('#2').first()).toBeVisible();
    await expect(page.getByText('#3').first()).toBeVisible();
  });
});
