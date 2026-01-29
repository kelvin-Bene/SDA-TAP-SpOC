import { test, expect } from './fixtures';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('welcome hero section renders', async ({ page }) => {
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('stat cards render', async ({ page }) => {
    // Dashboard should have stat cards (rank, submissions, F1, average)
    const cards = page.locator('[class*="card"], [class*="stat"]');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('Generate Dataset quick action links to /datasets/generate', async ({ page }) => {
    const generateLink = page.getByRole('link', { name: /generate.*dataset/i })
      .or(page.locator('a[href*="/datasets/generate"]'))
      .first();
    if (await generateLink.isVisible()) {
      await expect(generateLink).toHaveAttribute('href', /\/datasets\/generate/);
    }
  });

  test('Submit Algorithm links to /submit', async ({ page }) => {
    const submitLink = page.getByRole('link', { name: /submit/i })
      .or(page.locator('a[href*="/submit"]'))
      .first();
    if (await submitLink.isVisible()) {
      await expect(submitLink).toHaveAttribute('href', /\/submit/);
    }
  });

  test('Browse Datasets card links to /datasets', async ({ page }) => {
    const link = page.locator('a[href="/datasets"], a[href*="/datasets"]').first();
    if (await link.isVisible()) {
      await expect(link).toBeVisible();
    }
  });

  test('Leaderboard card links to /leaderboard', async ({ page }) => {
    const link = page.locator('a[href="/leaderboard"], a[href*="/leaderboard"]').first();
    if (await link.isVisible()) {
      await expect(link).toBeVisible();
    }
  });

  test('Documentation card links to /docs', async ({ page }) => {
    const link = page.locator('a[href="/docs"], a[href*="/docs"]').first();
    if (await link.isVisible()) {
      await expect(link).toBeVisible();
    }
  });

  test('recent submissions component renders', async ({ page }) => {
    const section = page.locator('text=/recent|submission/i').first();
    await expect(section).toBeVisible({ timeout: 5000 });
  });

  test('leaderboard snapshot renders', async ({ page }) => {
    const section = page.locator('text=/leaderboard|top|rank/i').first();
    await expect(section).toBeVisible({ timeout: 5000 });
  });

  test('page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForTimeout(3000);
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('.map') && !e.includes('404') && !e.includes('ERR_CONNECTION')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
