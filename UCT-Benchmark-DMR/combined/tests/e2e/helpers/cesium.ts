import { expect, type Page } from '@playwright/test';

/**
 * Helpers for asserting Cesium viewer health without relying on a window.* global.
 */

const DEFAULT_TIMEOUT = 20_000;

/** Wait for the Cesium canvas to be present and have non-trivial dimensions. */
export async function waitForCesiumCanvas(
  page: Page,
  opts: { timeout?: number; minSize?: number } = {},
): Promise<void> {
  const timeout = opts.timeout ?? DEFAULT_TIMEOUT;
  const minSize = opts.minSize ?? 200;
  await page.waitForFunction(
    (min: number) => {
      const c = document.querySelector('.cesium-viewer canvas') as HTMLCanvasElement | null;
      return !!c && c.clientWidth > min && c.clientHeight > min;
    },
    minSize,
    { timeout },
  );
}

/** Count cesium-viewer / cesium-widget DOM nodes (exposes leaked-viewer bugs). */
export async function countCesiumWidgets(page: Page): Promise<{ viewer: number; widget: number; canvas: number }> {
  return page.evaluate(() => ({
    viewer: document.querySelectorAll('.cesium-viewer').length,
    widget: document.querySelectorAll('.cesium-widget').length,
    canvas: document.querySelectorAll('.cesium-viewer canvas').length,
  }));
}

/** Assert the infoBox is NOT present (CSP compliance — avoids unsafe-eval in iframe). */
export async function assertNoCesiumInfoBox(page: Page): Promise<void> {
  const exists = await page.evaluate(() => !!document.querySelector('.cesium-infoBox'));
  expect(exists, 'Cesium infoBox must not be present (CSP unsafe-eval compliance)').toBe(false);
}

/** Read canvas dimensions of the Cesium canvas. */
export async function getCesiumCanvasSize(page: Page): Promise<{ w: number; h: number } | null> {
  return page.evaluate(() => {
    const c = document.querySelector('.cesium-viewer canvas') as HTMLCanvasElement | null;
    return c ? { w: c.clientWidth, h: c.clientHeight } : null;
  });
}

/** Fetch the CSP response header from the given URL. */
export async function fetchCspHeader(page: Page, url: string): Promise<string | null> {
  const response = await page.request.get(url);
  return response.headers()['content-security-policy'] || null;
}
