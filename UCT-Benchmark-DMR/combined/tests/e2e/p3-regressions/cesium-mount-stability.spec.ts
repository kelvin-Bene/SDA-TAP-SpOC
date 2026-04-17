import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas, countCesiumWidgets } from '../helpers/cesium';

/**
 * Guards commit fed4677 (direct Viewer mount via useEffect, no resium wrapper).
 * A reload should re-mount cleanly, no "Viewer has already been destroyed" errors.
 */
test.describe('P3 Regression — Cesium mount stability', () => {
  test('Cesium remounts successfully after page reload', async ({ page, consoleWatcher }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    await page.reload();
    await waitForCesiumCanvas(page);
    const counts = await countCesiumWidgets(page);
    expect(counts.viewer).toBe(1);
    expect(counts.canvas).toBe(1);
    expect(consoleWatcher.violations()).toEqual([]);
  });

  test('three reloads in a row do not accumulate widgets or errors', async ({ page, consoleWatcher }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    for (let i = 0; i < 3; i++) {
      await page.reload();
      await waitForCesiumCanvas(page);
      const counts = await countCesiumWidgets(page);
      expect(counts.viewer, `Reload ${i + 1} should leave 1 viewer`).toBe(1);
    }
    expect(consoleWatcher.violations()).toEqual([]);
  });
});
