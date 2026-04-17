import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas } from '../helpers/cesium';

/**
 * Exercise the Play/Pause, Reset, Zoom, and Speed controls.
 * Regression target: control handlers disconnecting from viewer or icon swap failing.
 */
test.describe('P3 Regression — Cesium controls', () => {
  test('Play/Pause button toggles icon (pause → play)', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);

    // Find the 4 control buttons — Play/Pause is first
    const initialIcon = await page.evaluate(() => {
      const btn = document.querySelectorAll('.cesium-viewer')[0]?.parentElement?.parentElement
        ?.querySelectorAll('button')[0];
      return btn?.firstElementChild?.className?.baseVal || '';
    });
    expect(initialIcon).toMatch(/lucide-(play|pause)/);

    // Click first control button
    const firstCtrlLocator = page.locator('.cesium-viewer').locator('..').locator('..').locator('button').first();
    await firstCtrlLocator.click();

    const toggledIcon = await page.evaluate(() => {
      const btn = document.querySelectorAll('.cesium-viewer')[0]?.parentElement?.parentElement
        ?.querySelectorAll('button')[0];
      return btn?.firstElementChild?.className?.baseVal || '';
    });
    expect(toggledIcon, 'Icon class should flip between play and pause').not.toBe(initialIcon);
  });

  test('Speed slider moves via keyboard and label updates', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);

    const slider = page.getByRole('slider').first();
    await slider.click();
    const before = await slider.getAttribute('aria-valuenow');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    const after = await slider.getAttribute('aria-valuenow');
    expect(Number(after)).toBeGreaterThan(Number(before));

    // Label should match aria-valuenow
    const labelText = await page.locator('text=/^\\d+x$/').first().textContent();
    expect(labelText).toBe(`${after}x`);
  });
});
