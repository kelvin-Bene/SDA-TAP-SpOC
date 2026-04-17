/**
 * C1: SubmitPage dataset dropdown should list ONLY datasets for which the
 *     backend reports `has_reference_orbits === true`. The previous
 *     date-only filter (createdAt >= 2026-04-09) let users pick post-Apr-9
 *     datasets that still lacked persisted reference state vectors, so
 *     every submission against them failed at the evaluator
 *     (QA_PROD_RUN_2026-04-17 C1).
 *
 * Strategy: fetch the full /datasets/ payload, compute submittable and
 * unsubmittable names, then open the dropdown and assert that no option
 * text contains an unsubmittable dataset name.
 */
import { test, expect } from '@playwright/test';

const API_BASE =
  process.env.PLAYWRIGHT_API_URL || 'https://backend-production-4b02.up.railway.app';

test.describe('C1 — SubmitPage eval-readiness filter', () => {
  test('dropdown lists only datasets with has_reference_orbits=true', async ({
    page,
    request,
  }) => {
    await page.goto('/submit');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Extract the user's Supabase JWT from localStorage so we can call the
    // API directly and compare against what the dropdown shows.
    const jwt = await page.evaluate(() => {
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
    });
    expect(jwt, 'could not read Supabase JWT from localStorage').toBeTruthy();

    const apiRes = await request.get(`${API_BASE}/api/v1/datasets?limit=100`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    expect(apiRes.ok(), `datasets list responded ${apiRes.status()}`).toBe(true);
    const apiBody = await apiRes.json();
    const apiItems = (Array.isArray(apiBody) ? apiBody : apiBody.items ?? []) as Array<{
      id: string | number;
      name: string;
      has_reference_orbits?: boolean;
    }>;

    const submittable = apiItems.filter((d) => d.has_reference_orbits === true);
    const unsubmittableNames = apiItems
      .filter((d) => d.has_reference_orbits !== true)
      .map((d) => d.name);

    // Open the dropdown.
    const trigger = page.getByRole('combobox').first().or(
      page.locator('[role="combobox"]').first()
    );
    await expect(trigger.first()).toBeVisible({ timeout: 10_000 });
    await trigger.first().click();
    await page.waitForTimeout(500);

    const options = page.locator('[role="option"]');
    const count = await options.count();

    if (submittable.length === 0) {
      // No eval-ready datasets exist — dropdown should be empty or show an
      // empty-state label. No further assertions possible.
      expect(
        count,
        'no eval-ready datasets in API, so dropdown should be empty too'
      ).toBe(0);
      return;
    }

    expect(
      count,
      'dropdown should contain at least one eval-ready dataset'
    ).toBeGreaterThan(0);

    // Assert: no option references a dataset that the API flagged as
    // not-eval-ready. (Name-substring check — Radix options render the
    // dataset name as the option label.)
    for (let i = 0; i < count; i++) {
      const text = await options.nth(i).innerText();
      for (const bad of unsubmittableNames) {
        if (!bad) continue;
        expect(
          text.includes(bad),
          `dropdown option "${text.slice(0, 80)}" exposes unsubmittable dataset "${bad}"`
        ).toBe(false);
      }
    }
  });
});
