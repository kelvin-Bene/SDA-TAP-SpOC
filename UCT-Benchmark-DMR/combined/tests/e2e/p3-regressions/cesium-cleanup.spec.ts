import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas, countCesiumWidgets } from '../helpers/cesium';

/**
 * Guards against viewer leaks: navigate away and back, verify exactly 1 widget exists.
 * A regression here means the viewer.destroy() in useEffect cleanup isn't running,
 * and each nav-back creates a new WebGL context (Chrome caps at 16).
 */
test.describe('P3 Regression — Cesium cleanup on navigation', () => {
  test('nav-away-and-back leaves exactly one widget', async ({ page, consoleWatcher }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    let counts = await countCesiumWidgets(page);
    expect(counts.viewer).toBe(1);
    expect(counts.canvas).toBe(1);

    for (let i = 0; i < 3; i++) {
      await page.goto('/docs');
      await expect(page.getByRole('heading', { name: /Documentation/i })).toBeVisible();
      await page.goto('/dashboard');
      await waitForCesiumCanvas(page);
      counts = await countCesiumWidgets(page);
      expect(counts.viewer, `Expected exactly 1 viewer after iteration ${i + 1}`).toBe(1);
      expect(counts.canvas).toBe(1);
    }
    expect(consoleWatcher.violations()).toEqual([]);
  });
});
