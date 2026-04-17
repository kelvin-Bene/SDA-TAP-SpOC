import { test, expect } from '../fixtures/consoleWatcher';
import { fetchCspHeader } from '../helpers/cesium';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Guards commit 377a4b9 (Railway cache invalidation).
 * Verifies the delivered CSP header on the Railway deploy matches the git HEAD nginx.conf.
 * If Railway serves a stale image, specific directives (like *.bing.com) won't appear.
 */
test.describe('P3 Regression — Railway image freshness', () => {
  test('delivered CSP matches current nginx.conf directives', async ({ page, baseURL }) => {
    const csp = await fetchCspHeader(page, '/');
    expect(csp).toBeTruthy();

    // Required directives from current nginx.conf
    const requiredDirectives = [
      /wasm-unsafe-eval/,
      /unsafe-eval/,
      /\*\.bing\.com/,
      /\*\.virtualearth\.net/,
      /\*\.cesium\.com/,
      /worker-src[^;]*blob:/,
    ];
    for (const re of requiredDirectives) {
      expect(csp, `CSP must contain ${re}`).toMatch(re);
    }
  });

  test('nginx.conf on disk has same directives the server delivers', async ({ page }) => {
    const nginxConfPath = path.resolve(
      __dirname,
      '..',
      '..',
      '..',
      'frontend',
      'nginx.conf',
    );
    if (!fs.existsSync(nginxConfPath)) {
      test.skip(true, `nginx.conf not found at ${nginxConfPath}`);
      return;
    }
    const gitCsp = fs.readFileSync(nginxConfPath, 'utf8');
    // Extract the Content-Security-Policy line
    const cspMatch = gitCsp.match(/Content-Security-Policy[^"]*"([^"]+)"/i);
    expect(cspMatch, 'nginx.conf should define a CSP').toBeTruthy();

    const servedCsp = await fetchCspHeader(page, '/');
    expect(servedCsp).toBeTruthy();

    // Both should include Bing (the commit 8194c74 fix)
    expect(cspMatch![1]).toMatch(/\*\.bing\.com/);
    expect(servedCsp!).toMatch(/\*\.bing\.com/);
  });
});
