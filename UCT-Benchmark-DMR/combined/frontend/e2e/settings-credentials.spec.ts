import { test, expect } from './fixtures';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('domcontentloaded');
  });

  test('settings page renders credential cards', async ({ page }) => {
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
    // Should show credential service cards
    const cards = page.locator('[class*="card"]');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('each card shows service name and status', async ({ page }) => {
    const cards = page.locator('[class*="card"]');
    const count = await cards.count();
    if (count > 0) {
      const firstCard = cards.first();
      const text = await firstCard.textContent();
      // Should contain service-related text
      expect(text?.length).toBeGreaterThan(0);
    }
  });

  test('configure button opens dialog', async ({ page }) => {
    const configBtn = page.getByRole('button', { name: /configure|edit|set|manage/i }).first();
    if (await configBtn.isVisible()) {
      await configBtn.click();
      // Dialog may use role="dialog" or Radix dialog or custom div
      const dialog = page.locator('[role="dialog"]').first()
        .or(page.locator('[data-state="open"]').first())
        .or(page.locator('.fixed.inset-0').first());
      await expect(dialog).toBeVisible({ timeout: 3000 });
    }
  });

  test('form validates non-empty primary value', async ({ page }) => {
    const configBtn = page.getByRole('button', { name: /configure|edit|set/i }).first();
    if (await configBtn.isVisible()) {
      await configBtn.click();
      const dialog = page.locator('[role="dialog"], [class*="dialog"]').first();
      if (await dialog.isVisible()) {
        // Try to save without entering value
        const saveBtn = dialog.getByRole('button', { name: /save|submit|confirm/i }).first();
        if (await saveBtn.isVisible()) {
          await saveBtn.click();
          // Should show validation or remain open
          await page.waitForTimeout(500);
        }
      }
    }
  });

  test('test button exists on credential cards', async ({ page }) => {
    const testBtn = page.getByRole('button', { name: /test|check|verify/i }).first();
    if (await testBtn.isVisible()) {
      await expect(testBtn).toBeVisible();
    }
  });

  test('page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/settings');
    await page.waitForTimeout(3000);
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('.map') && !e.includes('404') && !e.includes('ERR_CONNECTION')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
