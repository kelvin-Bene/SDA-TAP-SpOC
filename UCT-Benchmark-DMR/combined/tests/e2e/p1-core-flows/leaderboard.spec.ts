import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P1 Core — Leaderboard', () => {
  test('leaderboard shows podium + rankings table', async ({ page }) => {
    await page.goto('/leaderboard');
    await expect(page.getByRole('heading', { name: /Leaderboard/i })).toBeVisible();
    // Podium has #1, #2, #3
    await expect(page.getByText('#1').first()).toBeVisible();
    await expect(page.getByText('#2').first()).toBeVisible();
    await expect(page.getByText('#3').first()).toBeVisible();
  });

  test('rankings table has rows with F1 scores', async ({ page }) => {
    await page.goto('/leaderboard');
    await expect(page.getByRole('tab', { name: 'Rankings' })).toBeVisible();
    // F1 scores are formatted like "0.9420" in the table
    await expect(page.getByRole('main').getByText(/0\.\d{3,4}/).first()).toBeVisible();
  });

  test('performance trends tab renders LineChart', async ({ page }) => {
    await page.goto('/leaderboard');
    await page.getByRole('tab', { name: 'Performance Trends' }).click();
    await expect(page.getByRole('heading', { name: /F1-Score Trends/i })).toBeVisible();
    // Wait for chart to render
    await page.waitForTimeout(1000);
    const svgCount = await page.locator('svg').count();
    expect(svgCount).toBeGreaterThan(0);
  });

  test('filter dropdowns present', async ({ page }) => {
    await page.goto('/leaderboard');
    await expect(page.getByText(/Orbital Regime/i).first()).toBeVisible();
    await expect(page.getByText(/Data Tier/i).first()).toBeVisible();
    await expect(page.getByText(/Time Period/i).first()).toBeVisible();
    await expect(page.getByText(/Dataset/i).first()).toBeVisible();
  });
});
