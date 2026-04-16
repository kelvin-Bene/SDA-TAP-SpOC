/**
 * Orbits tab on ResultsPage — loads the CesiumGlobe lazily.
 *
 * WebGL in headless chromium can be flaky; we accept either a <canvas>
 * (Cesium rendering) or a WebGL-unavailable fallback panel as pass.
 * The regression we care about is the Orbits TAB being reachable and not
 * erroring.
 */
import { test, expect, APIRequestContext } from '@playwright/test';

const API_BASE =
  process.env.PLAYWRIGHT_API_URL || 'https://backend-production-4b02.up.railway.app';

async function getJwt(page: import('@playwright/test').Page): Promise<string> {
  await page.goto('/dashboard');
  return (await page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith('sb-') || !key.endsWith('-auth-token')) continue;
      const raw = localStorage.getItem(key);
      if (!raw) continue;
      try {
        const parsed = JSON.parse(raw);
        if (parsed?.access_token) return parsed.access_token as string;
      } catch {
        /* ignore */
      }
    }
    return '';
  })) || '';
}

async function findAnySubmission(
  request: APIRequestContext,
  jwt: string
): Promise<string | null> {
  const res = await request.get(`${API_BASE}/api/v1/submissions?limit=1`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok()) return null;
  const body = await res.json();
  const items = Array.isArray(body) ? body : body.items ?? [];
  return items.length > 0 ? String(items[0].id) : null;
}

test.describe('Results page — Orbits tab', () => {
  test('Orbits tab is reachable and does not crash', async ({ page, request }) => {
    const jwt = await getJwt(page);
    const id = await findAnySubmission(request, jwt);
    if (!id) {
      test.skip(true, 'no submissions on this account');
      return;
    }

    await page.goto(`/results/${id}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(1500);

    const orbitsTab = page.getByRole('tab', { name: /orbits/i }).first();
    await expect(orbitsTab).toBeVisible({ timeout: 10_000 });
    await orbitsTab.click();
    await page.waitForTimeout(1500);

    // Accept: Cesium canvas, OR a "no orbits" / error fallback panel.
    const canvas = page.locator('canvas');
    const fallback = page.locator(
      'text=/no orbit|no predicted|unavailable|could not|load failed|webgl|removed from storage|cannot be visualized|no data|nothing to display|not available/i'
    );
    // Either must be visible.
    const hasCanvas = await canvas.first().isVisible({ timeout: 10_000 }).catch(() => false);
    const hasFallback = await fallback.first().isVisible().catch(() => false);
    expect(hasCanvas || hasFallback, 'Orbits tab should show canvas OR a fallback message').toBe(
      true
    );
  });

  test('switching tabs does not throw', async ({ page, request }) => {
    const jwt = await getJwt(page);
    const id = await findAnySubmission(request, jwt);
    if (!id) {
      test.skip(true, 'no submissions');
      return;
    }

    await page.goto(`/results/${id}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(1200);

    const pageErrors: string[] = [];
    page.on('pageerror', (e) => pageErrors.push(e.message));

    for (const label of [/binary/i, /state/i, /residual/i, /satellite/i, /orbit/i]) {
      const tab = page.getByRole('tab', { name: label }).first();
      if (await tab.isVisible().catch(() => false)) {
        await tab.click();
        await page.waitForTimeout(500);
      }
    }

    expect(pageErrors, `page errors while switching tabs: ${pageErrors.join('\n')}`).toEqual([]);
  });
});
