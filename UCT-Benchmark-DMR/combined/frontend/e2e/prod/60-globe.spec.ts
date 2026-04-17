/**
 * 3D orbit globe visibility rules.
 *   - Owner sees a 3D orbit section on their own dataset detail page
 *   - Non-owner's dataset detail page does NOT render the 3D section
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

async function findOwnedId(request: APIRequestContext, jwt: string): Promise<string | null> {
  const res = await request.get(`${API_BASE}/api/v1/datasets?mine=true&limit=1`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  const body = await res.json();
  const items = Array.isArray(body) ? body : body.items ?? [];
  return items.length > 0 ? String(items[0].id) : null;
}

async function findUnownedId(
  request: APIRequestContext,
  jwt: string,
  _ownerId: string
): Promise<string | null> {
  // DatasetSummary does not expose user_id/owner_id, so the previous
  // predicate never matched and this test always skipped
  // (QA_PROD_RUN_2026-04-17 M6). Use set-difference between `?mine=true`
  // and the unfiltered list: any id that's visible but not "mine" is
  // necessarily owned by someone else.
  const headers = { Authorization: `Bearer ${jwt}` };
  const [mineRes, allRes] = await Promise.all([
    request.get(`${API_BASE}/api/v1/datasets?mine=true&limit=50`, { headers }),
    request.get(`${API_BASE}/api/v1/datasets?limit=50`, { headers }),
  ]);
  const mineBody = await mineRes.json();
  const allBody = await allRes.json();
  const mineItems = Array.isArray(mineBody) ? mineBody : mineBody.items ?? [];
  const allItems = Array.isArray(allBody) ? allBody : allBody.items ?? [];
  const mineIds = new Set<string>(mineItems.map((d: { id: number | string }) => String(d.id)));
  const other = allItems.find(
    (d: { id: number | string }) => !mineIds.has(String(d.id))
  );
  return other ? String(other.id) : null;
}

test.describe('3D orbit globe visibility', () => {
  test('owner sees a 3D orbit section on their dataset detail page', async ({ page, request }) => {
    const jwt = await getJwt(page);
    const ownedId = await findOwnedId(request, jwt);
    if (!ownedId) {
      test.skip(true, 'no owned datasets');
      return;
    }

    await page.goto(`/datasets/${ownedId}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(3000);

    // Look for any "3D" / "Orbit" header/section.
    const has3dSection = await page
      .locator('text=/3D Orbit|orbit preview|orbit viewer|orbits/i')
      .first()
      .isVisible({ timeout: 10_000 })
      .catch(() => false);
    expect(has3dSection).toBe(true);
  });

  test('non-owner dataset page does NOT render a 3D orbit section', async ({ page, request }) => {
    const jwt = await getJwt(page);
    const ownedId = await findOwnedId(request, jwt);
    if (!ownedId) {
      test.skip(true, 'cannot identify ownership');
      return;
    }
    const otherId = await findUnownedId(request, jwt, ownedId);
    if (!otherId) {
      test.skip(true, 'no other-user datasets visible');
      return;
    }

    await page.goto(`/datasets/${otherId}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(1500);

    // No "3D Orbit Preview" / "Reference Orbits" heading for non-owners.
    const has3dSection = await page
      .locator('text=/3D orbit preview|reference orbits/i')
      .first()
      .isVisible()
      .catch(() => false);
    expect(has3dSection).toBe(false);
  });
});
