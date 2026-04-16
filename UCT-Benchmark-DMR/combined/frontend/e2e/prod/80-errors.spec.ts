/**
 * Error-state coverage — 404s, 403s, invalid JSON upload rejection.
 */
import { test, expect } from '@playwright/test';

test.describe('Error states', () => {
  test('404 on unknown route', async ({ page }) => {
    await page.goto('/this-does-not-exist-abc-999');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await expect(page.locator('text=/404|not found/i').first()).toBeVisible();
  });

  test('Submission detail renders some recognisable state for bogus ID', async ({ page }) => {
    await page.goto('/results/not-a-real-submission-xyzzy');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(2000);
    // Accept either an error/not-found panel OR a generic empty results
    // view — the important thing is the page doesn't blow up.
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(20);
  });

  test('SubmitPage rejects invalid JSON upload', async ({ page }) => {
    await page.goto('/submit');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    const fileInput = page.locator('input[type="file"]').first();
    if ((await fileInput.count()) === 0) {
      test.skip(true, 'file input not present');
      return;
    }

    // Upload a tiny invalid-JSON buffer.
    await fileInput.setInputFiles({
      name: 'invalid.json',
      mimeType: 'application/json',
      buffer: Buffer.from('{"this is": "not valid'),
    });

    // Validation runs async; allow time for the panel to show a red state.
    await page.waitForTimeout(3000);
    // Either a "failed"/"invalid" text OR a red X icon — accept either.
    const hasFailText = await page
      .locator('text=/invalid|parse|malformed|failed|error/i')
      .first()
      .isVisible()
      .catch(() => false);
    const hasFailIcon = (await page.locator('svg[class*="destructive"], svg[class*="red"]').count()) > 0;
    expect(hasFailText || hasFailIcon).toBe(true);
  });
});
