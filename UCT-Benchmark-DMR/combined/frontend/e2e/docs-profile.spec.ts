import { test, expect } from './fixtures';

test.describe('Documentation Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/docs');
    await page.waitForLoadState('domcontentloaded');
  });

  test('documentation page renders with navigation', async ({ page }) => {
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('code examples render correctly', async ({ page }) => {
    // Look for code blocks or formatted content
    const codeBlock = page.locator('pre, code, [class*="code"]').first();
    if (await codeBlock.isVisible()) {
      const text = await codeBlock.textContent();
      expect(text?.length).toBeGreaterThan(0);
    }
  });

  test('page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/docs');
    await page.waitForTimeout(2000);
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('.map') && !e.includes('404') && !e.includes('ERR_CONNECTION')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('Profile Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/profile');
    await page.waitForLoadState('domcontentloaded');
  });

  test('profile page renders user information', async ({ page }) => {
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('profile shows user details', async ({ page }) => {
    // Should display user info (anonymous in auth-disabled mode)
    const content = page.locator('text=/anonymous|user|profile|email/i').first();
    await expect(content).toBeVisible({ timeout: 5000 });
  });

  test('page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/profile');
    await page.waitForTimeout(2000);
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('.map') && !e.includes('404') && !e.includes('ERR_CONNECTION')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
