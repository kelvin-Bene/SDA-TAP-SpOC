import { test, expect } from '../fixtures/consoleWatcher';
import { fetchCspHeader } from '../helpers/cesium';

test.describe('P0 Smoke — CSP sanity', () => {
  test('index.html returns a CSP header with required directives', async ({ page }) => {
    const csp = await fetchCspHeader(page, '/');
    expect(csp, 'CSP header must be present on HTML response').not.toBeNull();
    expect(csp).toMatch(/script-src[^;]*'wasm-unsafe-eval'/i);
    expect(csp).toMatch(/script-src[^;]*'unsafe-eval'/i);
    expect(csp).toMatch(/img-src[^;]*\*\.bing\.com/i);
    expect(csp).toMatch(/img-src[^;]*\*\.virtualearth\.net/i);
    expect(csp).toMatch(/img-src[^;]*\*\.cesium\.com/i);
    expect(csp).toMatch(/connect-src[^;]*\*\.cesium\.com/i);
    expect(csp).toMatch(/worker-src[^;]*blob:/i);
  });

  test('dashboard load produces zero CSP violations', async ({ page, consoleWatcher }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
    // Wait for Cesium chunks to finish — Cesium triggers CSP checks on script/worker/tile loads
    await page.waitForTimeout(5000);
    // consoleWatcher.assertClean() runs in fixture afterEach; if any CSP violation
    // or Refused-to-load appears, the test will fail automatically.
    expect(consoleWatcher.violations()).toEqual([]);
  });
});
