import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas } from '../helpers/cesium';

/**
 * The Cesium infoBox uses knockout.js which triggers unsafe-eval CSP violations.
 * It MUST remain disabled (infoBox: false in Viewer options).
 * If someone re-enables it, clicking an entity will crash the page.
 */
test.describe('P3 Regression — No Cesium infoBox', () => {
  test('no .cesium-infoBox element on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    const count = await page.locator('.cesium-infoBox').count();
    expect(count, 'Cesium infoBox must be disabled to comply with CSP').toBe(0);
  });

  test('no .cesium-infoBox element on dataset detail', async ({ page }) => {
    await page.goto('/datasets/1');
    await waitForCesiumCanvas(page);
    const count = await page.locator('.cesium-infoBox').count();
    expect(count).toBe(0);
  });
});
