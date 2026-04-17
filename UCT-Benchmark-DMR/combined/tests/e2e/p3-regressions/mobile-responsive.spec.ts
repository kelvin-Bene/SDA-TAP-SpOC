import { test, expect } from '../fixtures/consoleWatcher';
import { waitForCesiumCanvas } from '../helpers/cesium';
import { VIEWPORTS } from '../helpers/viewports';

/**
 * Guards commit f3d3062 — mobile responsiveness.
 * Assertions: no horizontal overflow; hamburger visible; Cesium scales down but still mounts.
 */
test.describe('P3 Regression — Mobile responsive', () => {
  test.use({ viewport: VIEWPORTS.MOBILE });

  test('dashboard at 375×812 has no horizontal overflow', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page, { minSize: 100 });
    const { scrollWidth, innerWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(scrollWidth, 'No horizontal overflow on mobile').toBeLessThanOrEqual(innerWidth + 1);
  });

  test('hamburger menu button visible on mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('button', { name: 'Toggle menu' })).toBeVisible();
  });

  test('Cesium canvas scales correctly on mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForCesiumCanvas(page, { minSize: 100 });
    const size = await page.evaluate(() => {
      const c = document.querySelector('.cesium-viewer canvas') as HTMLCanvasElement | null;
      return c ? { w: c.clientWidth, h: c.clientHeight } : null;
    });
    expect(size!.w).toBeGreaterThan(100);
    expect(size!.w).toBeLessThan(500); // scaled down from desktop 906
    expect(size!.h).toBeGreaterThan(200);
  });

  test('datasets cards stack vertically on mobile', async ({ page }) => {
    await page.goto('/datasets');
    await expect(page.getByRole('heading', { name: 'Datasets', level: 1 })).toBeVisible();
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(overflow, 'datasets page no h-overflow on mobile').toBe(false);
  });
});
