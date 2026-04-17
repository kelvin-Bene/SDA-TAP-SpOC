import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas, getCesiumCanvasSize, assertNoCesiumInfoBox } from '../helpers/cesium';

/**
 * Guards commits 8194c74, 377a4b9, fed4677 — CSP unsafe-eval + Bing whitelisting + resium bypass.
 * If any of these regresses, Cesium stops rendering and console fills with "Refused to..." errors.
 */
test.describe('P3 Regression — Cesium on /dashboard', () => {
  test('Cesium canvas mounts with non-trivial size', async ({ page, consoleWatcher }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    const size = await getCesiumCanvasSize(page);
    expect(size).not.toBeNull();
    expect(size!.w).toBeGreaterThan(200);
    expect(size!.h).toBeGreaterThan(200);
    expect(consoleWatcher.violations()).toEqual([]);
  });

  test('no CSP violations during Cesium init + 5s of tile loading', async ({ page, consoleWatcher }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    await page.waitForTimeout(5000);
    expect(consoleWatcher.violations()).toEqual([]);
  });

  test('infoBox NOT present (unsafe-eval compliance)', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    await assertNoCesiumInfoBox(page);
  });

  test('Bing/Cesium tile hosts return 2xx responses', async ({ page }) => {
    const responses: { url: string; status: number }[] = [];
    page.on('response', (r) => {
      const u = r.url();
      if (/virtualearth\.net|bing\.com|cesium\.com|ion\.cesium\.com/.test(u)) {
        responses.push({ url: u, status: r.status() });
      }
    });
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    await page.waitForTimeout(5000);
    expect(responses.length, 'Expected at least one Cesium/Bing asset response').toBeGreaterThan(0);
    const bad = responses.filter((r) => r.status >= 400 && r.status !== 401);
    expect(bad, `CDN responses with unexpected error status: ${JSON.stringify(bad)}`).toEqual([]);
  });
});
