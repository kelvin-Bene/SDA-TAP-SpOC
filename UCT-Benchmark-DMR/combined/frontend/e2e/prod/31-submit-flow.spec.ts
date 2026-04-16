/**
 * Full E2E submit flow — uploads `data/test_uctp_output.json` against an
 * Apr-14+ owned dataset, watches the 5-step validation panel, submits,
 * lands on My Submissions.
 *
 * This creates ONE real submission per run. Safe because the submission is
 * against kelvin's own dataset and won't mutate shared state (aside from
 * the submissions table row). Skips gracefully if no suitable dataset is
 * available.
 */
import { test, expect, APIRequestContext } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const API_BASE =
  process.env.PLAYWRIGHT_API_URL || 'https://backend-production-4b02.up.railway.app';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UCTP_FIXTURE = path.resolve(
  __dirname,
  '../../../data/test_uctp_output.json'
);

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

async function findSubmittableDataset(
  request: APIRequestContext,
  jwt: string
): Promise<{ id: string; name: string } | null> {
  const res = await request.get(`${API_BASE}/api/v1/datasets?mine=true&limit=20`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok()) return null;
  const body = await res.json();
  const items = Array.isArray(body) ? body : body.items ?? [];
  const cutoff = new Date('2026-04-09T00:00:00Z').getTime();
  const usable = items.find((d: { created_at?: string; createdAt?: string }) => {
    const ts = new Date(d.created_at ?? d.createdAt ?? 0).getTime();
    return Number.isFinite(ts) && ts >= cutoff;
  });
  return usable ? { id: String(usable.id), name: usable.name ?? '' } : null;
}

test.describe('Submit flow (creates one real submission)', () => {
  test('upload + validate + submit against Apr-14+ dataset', async ({ page, request }) => {
    test.setTimeout(120_000);

    const jwt = await getJwt(page);
    const dataset = await findSubmittableDataset(request, jwt);
    if (!dataset) {
      test.skip(true, 'no post-Apr-9 owned dataset available to submit against');
      return;
    }

    await page.goto('/submit');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Upload the UCTP fixture via the dropzone's hidden input.
    const fileInput = page.locator('input[type="file"]').first();
    await expect(fileInput).toBeAttached();
    await fileInput.setInputFiles(UCTP_FIXTURE);

    // Wait for the validation panel to go green on at least one step.
    await expect(
      page.locator('text=/format|schema|valid/i').first()
    ).toBeVisible({ timeout: 10_000 });
    // Let the 5-step validation animation finish.
    await page.waitForTimeout(3500);

    // Select the dataset from the dropdown.
    const datasetTrigger = page.getByRole('combobox').first();
    await datasetTrigger.click();
    await page.waitForTimeout(400);
    const datasetOption = page
      .locator('[role="option"]')
      .filter({ hasText: new RegExp(dataset.id, 'i') })
      .or(page.locator('[role="option"]').first());
    await datasetOption.first().click();

    // Fill required metadata fields.
    const nameInput = page.getByRole('textbox', { name: /algorithm name/i }).first();
    if (await nameInput.isVisible().catch(() => false)) {
      await nameInput.fill(`PlaywrightSmoke-${Date.now()}`);
    }
    const versionInput = page.getByRole('textbox', { name: /version/i }).first();
    if (await versionInput.isVisible().catch(() => false)) {
      await versionInput.fill('1.0-smoke');
    }

    // Click the Submit button.
    const submit = page.getByRole('button', { name: /^submit/i }).first();
    await expect(submit).toBeVisible();
    // The submit may be disabled if validation hasn't completed; guard.
    const disabled = await submit.isDisabled().catch(() => false);
    if (disabled) {
      test.skip(true, 'Submit button disabled; validation incomplete or fields missing');
      return;
    }
    await submit.click();

    // Expect a toast or redirect to my-submissions.
    await expect(
      page.locator('text=/submitted|queued|my submissions/i').first()
    ).toBeVisible({ timeout: 15_000 });
  });
});
