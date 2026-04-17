import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas } from '../helpers/cesium';

/**
 * Guards CSP img-src whitelisting for Bing tiles (commit 8194c74).
 * Collect network responses from all Cesium/Bing hosts and assert at least one 200 tile.
 */
test.describe('P3 Regression — Cesium Bing tile loading', () => {
  test('at least one Bing/virtualearth tile loads successfully', async ({ page }) => {
    const tileResponses: { url: string; status: number }[] = [];
    page.on('response', (r) => {
      if (/virtualearth\.net|\.bing\.com/.test(r.url())) {
        tileResponses.push({ url: r.url(), status: r.status() });
      }
    });
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    await page.waitForTimeout(5000);

    expect(tileResponses.length).toBeGreaterThan(0);
    const ok = tileResponses.filter((r) => r.status >= 200 && r.status < 300);
    expect(ok.length, 'At least one Bing tile must return 2xx').toBeGreaterThan(0);
  });

  test('Cesium ion endpoint returns success', async ({ page }) => {
    const ionResponses: { url: string; status: number }[] = [];
    page.on('response', (r) => {
      if (/api\.cesium\.com|assets\.cesium\.com|ion\.cesium\.com/.test(r.url())) {
        ionResponses.push({ url: r.url(), status: r.status() });
      }
    });
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page);
    await page.waitForTimeout(3000);

    expect(ionResponses.length, 'Expected at least one Cesium ion API call').toBeGreaterThan(0);
    const bad = ionResponses.filter((r) => r.status >= 500);
    expect(bad, 'No 5xx errors from Cesium ion').toEqual([]);
  });
});
