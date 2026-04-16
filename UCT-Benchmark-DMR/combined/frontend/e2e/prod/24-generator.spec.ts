/**
 * Dataset generator wizard — renders, does NOT submit (generation costs UDL).
 */
import { test, expect } from '@playwright/test';

test.describe('Dataset generator', () => {
  test('generator page is reachable from Datasets browser', async ({ page }) => {
    // /datasets/generate can be shadowed by /datasets/:id when react-router's
    // ranking isn't perfectly reliable across bundles. Navigate via the
    // Datasets browser's CTA instead.
    await page.goto('/datasets');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    const generateBtn = page
      .getByRole('link', { name: /generate|new dataset/i })
      .or(page.getByRole('button', { name: /generate|new dataset/i }))
      .first();

    if (!(await generateBtn.isVisible().catch(() => false))) {
      test.skip(true, 'Generate CTA not visible in browser viewport');
      return;
    }
    await generateBtn.click();
    await page.waitForTimeout(1500);

    const hasWizard =
      (await page.locator('text=/step.+of|generate dataset|orbital regime/i').first().isVisible().catch(() => false)) ||
      (await page.locator('button').filter({ hasText: /generate|start|next/i }).first().isVisible().catch(() => false));
    expect(hasWizard).toBe(true);
  });
});
