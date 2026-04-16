/**
 * B2: ResultsPage shows an "Evaluation Failed" banner + dimmed metric cards
 *     when submission.status === 'failed'. The error_message from the
 *     backend must be threaded through the useSubmissions hook.
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

async function findFailedSubmission(
  request: APIRequestContext,
  jwt: string
): Promise<string | null> {
  const res = await request.get(`${API_BASE}/api/v1/submissions?status=failed&limit=5`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok()) return null;
  const body = await res.json();
  const items = Array.isArray(body) ? body : body.items ?? [];
  return items.length > 0 ? String(items[0].id) : null;
}

test.describe('B2 — Failed evaluation UI', () => {
  test('failed submission shows banner + dimmed metrics', async ({ page, request }) => {
    const jwt = await getJwt(page);
    const failedId = await findFailedSubmission(request, jwt);

    if (!failedId) {
      test.skip(true, 'no failed submissions on this account — acceptable prod state');
      return;
    }

    await page.goto(`/results/${failedId}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(1200);

    // Banner heading is exactly "Evaluation Failed".
    await expect(
      page.locator('text=/evaluation failed/i').first()
    ).toBeVisible({ timeout: 10_000 });

    // Metric-card grid is dimmed via opacity-40 utility class.
    // Locate the grid that wraps the Summary Cards — it follows the banner.
    const dimmedGrid = page.locator('.opacity-40').first();
    await expect(dimmedGrid).toBeVisible();
  });
});
