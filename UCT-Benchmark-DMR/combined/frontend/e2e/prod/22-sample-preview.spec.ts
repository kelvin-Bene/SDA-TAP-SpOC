/**
 * B3: DatasetPreviewDialog Sample Data tab shows the real 11-field schema
 *     (obTime, ra, declination, azimuth, elevation, senlat, senlon, senalt,
 *     idSensor, trackId, split) and NO truthCatalog / satId / state / noradId.
 *
 * Today's fix replaced a hardcoded JSX fixture that was misrepresenting the
 * answer-key separation (showed truthCatalog + satId). This spec guards
 * against regression.
 */
import { test, expect } from '@playwright/test';

test.describe('B3 — Sample Data preview fixture', () => {
  test('Sample Data tab shows 11-field schema and no answer-key fields', async ({ page }) => {
    await page.goto('/datasets');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Open the first dataset card's Preview. Dataset cards have a "Preview"
    // button or the whole card is clickable. Be flexible.
    const previewBtn = page.getByRole('button', { name: /preview/i }).first();
    await expect(previewBtn).toBeVisible({ timeout: 10_000 });
    await previewBtn.click();

    // Dialog opens. Click Sample tab.
    const sampleTab = page.getByRole('tab', { name: /sample/i }).first();
    await expect(sampleTab).toBeVisible({ timeout: 5_000 });
    await sampleTab.click();

    // The <pre> block inside the dialog should contain the real schema.
    const preText = await page.locator('[role="dialog"] pre, dialog pre, .fixed pre').first().innerText();

    // Required field names (the 11-field whitelist + metadata keys).
    for (const field of [
      'obTime',
      'declination',
      'azimuth',
      'elevation',
      'senlat',
      'senlon',
      'senalt',
      'idSensor',
      'trackId',
      'split',
    ]) {
      expect(preText, `expected ${field} in Sample preview`).toContain(field);
    }

    // Explicitly forbidden answer-key leakage strings.
    for (const forbidden of ['truthCatalog', 'satId', '"state"', 'noradId']) {
      expect(preText.toLowerCase(), `${forbidden} must not appear in sample preview`).not.toContain(
        forbidden.toLowerCase()
      );
    }
  });
});
