/**
 * Dataset detail page.
 *
 * Covers:
 *   - Owned dataset detail renders
 *   - M6: 404 for missing dataset shows friendly "No dataset exists with ID..." copy
 *   - Download of owned dataset succeeds and has no answer-key fields
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

async function findOwnedDatasetId(
  request: APIRequestContext,
  jwt: string
): Promise<string | null> {
  const res = await request.get(`${API_BASE}/api/v1/datasets?mine=true&limit=1`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok()) return null;
  const body = await res.json();
  const items = Array.isArray(body) ? body : body.items ?? [];
  return items.length > 0 ? String(items[0].id) : null;
}

test.describe('Dataset detail', () => {
  test('owned dataset page renders', async ({ page, request }) => {
    const jwt = await getJwt(page);
    const id = await findOwnedDatasetId(request, jwt);
    if (!id) {
      test.skip(true, 'no owned datasets');
      return;
    }

    await page.goto(`/datasets/${id}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    // Expect the dataset name or ID to render somewhere.
    await expect(page.locator('body')).toContainText(/dataset|regime|tier/i, {
      timeout: 10_000,
    });
  });

  test('M6: 404 shows friendly "No dataset exists with ID" copy', async ({ page }) => {
    await page.goto('/datasets/does-not-exist-xyzzy-9999');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    await expect(
      page.locator('text=/no dataset exists with id|not found/i').first()
    ).toBeVisible({ timeout: 10_000 });

    // The raw axios message should NOT leak.
    const body = (await page.locator('body').innerText()).toLowerCase();
    expect(body).not.toContain('request failed with status code');
  });

  test('owned dataset download response has no answer-key fields', async ({
    request,
    page,
  }) => {
    const jwt = await getJwt(page);
    const id = await findOwnedDatasetId(request, jwt);
    if (!id) {
      test.skip(true, 'no owned datasets to download');
      return;
    }

    const res = await request.get(`${API_BASE}/api/v1/datasets/${id}/download`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    expect(res.status()).toBe(200);
    const text = await res.text();
    // Parse enough to check the top-level shape.
    const parsed = JSON.parse(text);
    expect(parsed).toHaveProperty('observations');
    expect(parsed).not.toHaveProperty('truthCatalog');
    expect(parsed).not.toHaveProperty('truth_catalog');
    // Sample a couple of observations.
    const obs = parsed.observations?.slice?.(0, 3) ?? [];
    for (const o of obs) {
      expect(o).not.toHaveProperty('satId');
      expect(o).not.toHaveProperty('satNo');
      expect(o).not.toHaveProperty('state');
      expect(o).not.toHaveProperty('noradId');
    }
  });
});
