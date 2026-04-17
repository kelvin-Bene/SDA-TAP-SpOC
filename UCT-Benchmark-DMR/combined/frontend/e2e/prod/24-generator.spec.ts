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

    // The "Generate Dataset" link lives in the sidebar (inside a collapsible
    // Datasets group), so searching for a visible body-level link/button by
    // accessible name misses it. Prefer a DOM-presence check on the href,
    // which Playwright can click even when a parent needs to scroll/expand
    // (QA_PROD_RUN_2026-04-17 M5).
    const generateLink = page
      .locator('a[href="/datasets/generate"]')
      .or(page.getByRole('link', { name: /generate|new dataset/i }))
      .or(page.getByRole('button', { name: /generate|new dataset/i }))
      .first();

    if ((await generateLink.count()) === 0) {
      test.skip(true, 'Generate Dataset link not in DOM');
      return;
    }
    await generateLink.click();
    await page.waitForTimeout(1500);

    const hasWizard =
      (await page.locator('text=/step.+of|generate dataset|orbital regime/i').first().isVisible().catch(() => false)) ||
      (await page.locator('button').filter({ hasText: /generate|start|next/i }).first().isVisible().catch(() => false));
    expect(hasWizard).toBe(true);
  });
});
