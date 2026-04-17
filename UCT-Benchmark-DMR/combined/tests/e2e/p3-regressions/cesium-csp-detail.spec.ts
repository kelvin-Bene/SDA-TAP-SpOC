import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas, getCesiumCanvasSize, assertNoCesiumInfoBox } from '../helpers/cesium';

/**
 * Cesium also mounts on /datasets/:id. Verify the second mount is clean.
 * Guards against Cesium regressions specific to detail-page embed (Regime-specific rendering).
 */
test.describe('P3 Regression — Cesium on /datasets/:id', () => {
  test('Cesium canvas mounts on dataset detail page', async ({ page, consoleWatcher }) => {
    await page.goto('/datasets/1');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/LEO|MEO|GEO|HEO|T\d/);
    await waitForCesiumCanvas(page);
    const size = await getCesiumCanvasSize(page);
    expect(size!.w).toBeGreaterThan(200);
    expect(size!.h).toBeGreaterThan(200);
    expect(consoleWatcher.violations()).toEqual([]);
  });

  test('detail page has no infoBox', async ({ page }) => {
    await page.goto('/datasets/1');
    await waitForCesiumCanvas(page);
    await assertNoCesiumInfoBox(page);
  });
});
