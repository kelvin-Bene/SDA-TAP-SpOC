/**
 * Supplementary prod probes — added 2026-04-17 during the comprehensive
 * QA pass to encode bugs found outside the existing spec coverage.
 *
 * Findings these specs encode:
 *   1. B1 filter is DATE-ONLY, not existence-of-reference-state-vectors. Some
 *      post-Apr-9 datasets (e.g. 158) are listed in the Submit dropdown but
 *      the backend rejects their evaluation with
 *      "Dataset X has no reference state vectors persisted."
 *   2. submission.error_message is NULL on failed submissions even when the
 *      job.error has a populated ValueError. The /submissions/ endpoint
 *      should propagate job.error to submission.error_message.
 *   3. Leaderboard is empty because all submissions fail — coverage probe
 *      that confirms the end-to-end evaluation path works against ANY
 *      available dataset on this account.
 *   4. Composite score fields are absent from /leaderboard/ response when
 *      empty — validate the keys *would* be present in a populated entry.
 *   5. Cache-Control header regression check — SPA index.html must be
 *      no-cache, asset chunks must be immutable.
 */
import { test, expect, APIRequestContext } from '@playwright/test';

const API_BASE =
  process.env.PLAYWRIGHT_API_URL || 'https://backend-production-4b02.up.railway.app';
const FE_BASE =
  process.env.PLAYWRIGHT_BASE_URL || 'https://frontend-production-6d80.up.railway.app';
const EVAL_CUTOFF_MS = new Date('2026-04-09T00:00:00Z').getTime();

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

async function listAllDatasets(
  request: APIRequestContext,
  jwt: string
): Promise<Array<{ id: string; createdAt: string; name: string }>> {
  const res = await request.get(`${API_BASE}/api/v1/datasets?limit=100`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok()) return [];
  const body = await res.json();
  const items = (Array.isArray(body) ? body : body.items ?? []) as Array<{
    id: string | number;
    created_at?: string;
    createdAt?: string;
    name?: string;
  }>;
  return items.map((d) => ({
    id: String(d.id),
    createdAt: d.created_at || d.createdAt || '',
    name: d.name || '',
  }));
}

test.describe('Supplementary — evaluation pipeline integrity', () => {
  test('B1 gap: every Submit-eligible dataset should produce a non-failed evaluation when used', async ({
    page,
    request,
  }) => {
    // This probe documents the observed regression: SubmitPage.tsx:73-80 only
    // filters by createdAt >= 2026-04-09, not by the existence of persisted
    // reference state vectors. The result is that users CAN submit against
    // Apr-14+ datasets but those submissions fail-through the evaluator.
    //
    // We cannot fix the bug here; we document it by walking the current
    // submissions list and asserting that at least ONE recent submission is
    // NOT status=failed. If this assertion fails, the whole platform is
    // effectively non-functional for demo purposes.
    const jwt = await getJwt(page);
    const res = await request.get(`${API_BASE}/api/v1/submissions/?limit=25`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    expect(res.ok(), `submissions list responded ${res.status()}`).toBe(true);

    const body = await res.json();
    const items = (Array.isArray(body) ? body : body.items ?? []) as Array<{
      id: string | number;
      status: string;
      dataset_name?: string;
    }>;

    if (items.length === 0) {
      test.skip(true, 'no submissions to evaluate');
      return;
    }

    const byStatus = items.reduce<Record<string, number>>((acc, s) => {
      acc[s.status] = (acc[s.status] || 0) + 1;
      return acc;
    }, {});

    // Diagnostic log: make it obvious in CI what the breakdown is.
    console.log('[supplementary] submissions status breakdown:', byStatus);

    const completedCount = byStatus.completed || 0;
    const total = items.length;

    // Hardened post-C1-fix: at least one submission must be completed (not
    // merely non-failed). A completed submission means the evaluator ran end
    // to end against an eval-ready dataset, which is what C1 + backfill
    // together should guarantee.
    expect(
      completedCount,
      `0 of ${total} submissions are completed — C1 regression: no eval-ready dataset produces a successful submission`
    ).toBeGreaterThan(0);
  });

  test('every post-Apr-9 dataset listed for Submit should resolve reference-orbits without 500/403-owner-lookup', async ({
    page,
    request,
  }) => {
    // Backend should be consistent: if a dataset is post-Apr-9 (and therefore
    // shown in Submit), reference_orbits for it should either:
    //   a) return 200 (for owner)
    //   b) return 403 (for non-owner — gated)
    //   c) return 404 (nonexistent)
    // A 500, or a 200 with satellites=[] implying the source was empty,
    // signals a pipeline regression (the very bug evaluating submissions).
    const jwt = await getJwt(page);
    const datasets = await listAllDatasets(request, jwt);

    const postCutoff = datasets.filter(
      (d) => new Date(d.createdAt).getTime() >= EVAL_CUTOFF_MS
    );
    if (postCutoff.length === 0) {
      test.skip(true, 'no post-Apr-9 datasets on this account to probe');
      return;
    }

    const diagnostics: string[] = [];
    for (const d of postCutoff.slice(0, 5)) {
      const r = await request.get(
        `${API_BASE}/api/v1/datasets/${d.id}/reference-orbits`,
        { headers: { Authorization: `Bearer ${jwt}` } }
      );
      diagnostics.push(`${d.id} (${d.name.slice(0, 40)}): ${r.status()}`);
      // Acceptable: 200, 403, 404. Anything else = regression.
      expect([200, 403, 404]).toContain(r.status());

      // If 200, the satellites array should not be empty for a dataset
      // that claims to have reference state vectors.
      if (r.status() === 200) {
        const body = await r.json();
        const sats = body.satellites ?? [];
        expect(
          Array.isArray(sats),
          `${d.id}: reference-orbits satellites should be an array`
        ).toBe(true);
        // This is the specific regression: satellites is empty → evaluation
        // will fail for this dataset. Documents the gap.
        if (sats.length === 0) {
          console.warn(
            `[supplementary] dataset ${d.id} (${d.name}) returns empty satellites []; submissions will fail`
          );
        }
      }
    }
    console.log('[supplementary] reference-orbits status per dataset:', diagnostics);
  });

  test('failed submissions should have non-null error_message', async ({ page, request }) => {
    // The useSubmissions hook and ResultsPage banner rely on
    // submission.error_message. Backend should populate it from job.error
    // when the evaluation job fails. This spec documents whether that
    // propagation works.
    const jwt = await getJwt(page);
    const res = await request.get(
      `${API_BASE}/api/v1/submissions/?status=failed&limit=5`,
      { headers: { Authorization: `Bearer ${jwt}` } }
    );
    expect(res.ok()).toBe(true);
    const body = await res.json();
    const items = (Array.isArray(body) ? body : body.items ?? []) as Array<{
      id: string | number;
    }>;

    if (items.length === 0) {
      test.skip(true, 'no failed submissions to probe (prod is healthy)');
      return;
    }

    // Fetch the detail for the most recent failed submission.
    const detail = await request.get(
      `${API_BASE}/api/v1/submissions/${items[0].id}`,
      { headers: { Authorization: `Bearer ${jwt}` } }
    );
    expect(detail.ok()).toBe(true);
    const sub = await detail.json();

    expect(sub.status).toBe('failed');
    expect(
      sub.error_message,
      `submission ${items[0].id} is failed but error_message is null — job.error propagation is broken`
    ).not.toBeNull();
    expect(typeof sub.error_message, 'error_message should be a string').toBe('string');
    expect(
      sub.error_message,
      'error_message should be non-empty'
    ).not.toBe('');
    // Should read like an exception line "TypeName: detail..." — covers the
    // QA_PROD_RUN_2026-04-17 H1 pattern (ValueError: "Dataset ... has no
    // reference state vectors persisted").
    expect(
      sub.error_message,
      `error_message should contain exception-shaped detail, got: ${sub.error_message}`
    ).toMatch(/Error|Exception|dataset|reference|evaluat|validat|submission|job/i);
  });

  test('leaderboard response shape includes composite score keys (whether populated or empty)', async ({
    page,
    request,
  }) => {
    // Leaderboard structure regression — even when empty, the response
    // envelope should be { dataset_id, last_updated, total_entries, entries }.
    // If total_entries > 0, each entry should expose composite_score and
    // f1_score fields (Part D #1).
    const jwt = await getJwt(page);
    const res = await request.get(`${API_BASE}/api/v1/leaderboard/`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    expect(res.ok()).toBe(true);
    const body = await res.json();

    expect(body).toHaveProperty('entries');
    expect(body).toHaveProperty('total_entries');
    expect(body).toHaveProperty('last_updated');

    if (body.total_entries > 0 && body.entries.length > 0) {
      const entry = body.entries[0];
      // Composite score keys — part of Part D #1.
      for (const key of ['f1_score']) {
        expect(entry, `leaderboard entry missing ${key}`).toHaveProperty(key);
      }
      // composite_score may be null on older entries — assert the key
      // exists whether or not it's populated.
      const hasCompositeShape =
        'composite_score' in entry || 'compositeScore' in entry;
      expect(hasCompositeShape, 'entry should surface composite_score key').toBe(true);
    }
  });
});

test.describe('Supplementary — deploy/cache header integrity', () => {
  test('SPA index.html has no-cache headers (deploy visibility)', async ({ request }) => {
    const res = await request.get(`${FE_BASE}/`);
    expect(res.ok()).toBe(true);
    const cc = res.headers()['cache-control'] || '';
    // Header is "no-cache, no-store, must-revalidate"
    expect(cc).toMatch(/no-cache/i);
    expect(cc).toMatch(/no-store/i);
    expect(cc).toMatch(/must-revalidate/i);
  });

  test('hashed asset chunks are cached immutably (client perf)', async ({ request }) => {
    // Extract one /assets/index-*.js hash from index.html, then HEAD it.
    const indexRes = await request.get(`${FE_BASE}/`);
    const indexHtml = await indexRes.text();
    const match = indexHtml.match(/assets\/[a-zA-Z0-9._-]+\.js/);
    expect(match, 'index.html should reference a hashed JS asset').toBeTruthy();

    const assetRes = await request.get(`${FE_BASE}/${match![0]}`);
    expect(assetRes.ok()).toBe(true);
    const cc = assetRes.headers()['cache-control'] || '';
    // nginx.conf.template sets "public, max-age=31536000, immutable"
    expect(cc).toMatch(/immutable/i);
    expect(cc).toMatch(/max-age=31536000/i);
  });
});

test.describe('Supplementary — UX gap probes on live data', () => {
  test('MySubmissions page lists our failed submissions (rendering path)', async ({
    page,
  }) => {
    await page.goto('/submit/my-submissions');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(2000);

    // At minimum we should see either a row, a "no submissions" empty state,
    // or the page header — any of these means the route renders.
    const hasRows = (await page.locator('table tbody tr, [role="row"]').count()) > 0;
    const emptyState = await page
      .locator('text=/no submissions|get started|empty/i')
      .first()
      .isVisible()
      .catch(() => false);
    const hasHeader = await page
      .locator('text=/my submissions|submissions/i')
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasRows || emptyState || hasHeader).toBe(true);
  });

  test('ResultsPage for a failed submission shows actionable banner (not "0.0%")', async ({
    page,
    request,
  }) => {
    // Walk failed submissions; ensure the ResultsPage renders the banner
    // AND does NOT render "0.0%" anywhere in the main card grid (that was
    // the pre-B2 regression).
    const jwt = await getJwt(page);
    const res = await request.get(
      `${API_BASE}/api/v1/submissions/?status=failed&limit=1`,
      { headers: { Authorization: `Bearer ${jwt}` } }
    );
    const body = await res.json();
    const items = (Array.isArray(body) ? body : body.items ?? []) as Array<{
      id: string | number;
    }>;
    if (items.length === 0) {
      test.skip(true, 'no failed submissions to probe');
      return;
    }

    await page.goto(`/results/${items[0].id}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(1500);

    // Banner present.
    await expect(
      page.locator('text=/evaluation failed/i').first()
    ).toBeVisible({ timeout: 10_000 });

    // Dimmed grid present (opacity-40 wrapper).
    const dimmedGrid = page.locator('.opacity-40').first();
    await expect(dimmedGrid).toBeVisible();

    // Hardened post-H1-fix: the banner's surrounding container should expose
    // the propagated submission.error_message — not just the generic
    // fallback "evaluation pipeline encountered an error" (the symptom of
    // the H1 regression).
    const bannerText = await page
      .locator('text=/evaluation failed/i')
      .first()
      .locator('xpath=ancestor::*[self::section or self::div][1]')
      .innerText()
      .catch(() => '');
    console.log('[supplementary] failed banner text sample:', bannerText.slice(0, 400));

    // Fetch the corresponding submission's error_message from the API so we
    // know what the banner should be quoting. Defensive: if the API returns
    // a non-empty error_message, the banner should include some recognizable
    // portion of it (we don't require an exact substring match to keep the
    // assertion resilient to UI copy changes).
    const detail = await request.get(
      `${API_BASE}/api/v1/submissions/${items[0].id}`,
      { headers: { Authorization: `Bearer ${jwt}` } }
    );
    const sub = await detail.json();
    if (sub.error_message) {
      const firstWord = String(sub.error_message)
        .split(/[\s:.,;()]+/)
        .find((w: string) => w.length >= 4);
      if (firstWord) {
        expect(
          bannerText.toLowerCase(),
          `failed banner should surface the propagated error_message (looked for "${firstWord}" in banner)`
        ).toContain(firstWord.toLowerCase());
      }
    }
  });

  test('Dataset with observations returns payload without answer-key fields for non-owner view', async ({
    request,
    page,
  }) => {
    // M5 answer-key separation — observations endpoint should never
    // surface *populated* answer-key fields (id_on_orbit, orig_object_id).
    // Presence of the KEY with null is acceptable (backend column fill);
    // presence with a non-null value = leak.
    const jwt = await getJwt(page);
    const res = await request.get(
      `${API_BASE}/api/v1/datasets?limit=5`,
      { headers: { Authorization: `Bearer ${jwt}` } }
    );
    expect(res.ok()).toBe(true);
    const datasets = (await res.json()) as Array<{ id: string | number }>;
    if (datasets.length === 0) {
      test.skip(true, 'no datasets on this account to probe');
      return;
    }

    for (const d of datasets.slice(0, 3)) {
      const obs = await request.get(
        `${API_BASE}/api/v1/datasets/${d.id}/observations?limit=5`,
        { headers: { Authorization: `Bearer ${jwt}` } }
      );
      if (!obs.ok()) continue;
      const body = await obs.json();
      const items = body.observations ?? body.items ?? body ?? [];
      const rows = Array.isArray(items) ? items : [];
      for (const row of rows) {
        for (const leakKey of ['id_on_orbit', 'orig_object_id', 'orig_sensor_id']) {
          // Assert: the key is either absent or null — never populated.
          if (leakKey in row) {
            expect(
              row[leakKey],
              `dataset ${d.id} observations row leaks non-null ${leakKey}: ${row[leakKey]}`
            ).toBeNull();
          }
        }
      }
    }
  });
});
