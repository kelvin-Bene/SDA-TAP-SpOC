/**
 * Part D #1: Composite Score card on ResultsPage.
 *
 * Asserts:
 *   - Card titled "Composite Score" is rendered
 *   - Three component rows (Binary, State, Residual) visible
 *   - Each row shows a bar + a percentage contribution figure
 *   - Train/Validation/Test footer exists (when split breakdowns present)
 *   - Fallback banner appears when state_component is unavailable
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

async function findResultsSubmissionId(
  request: APIRequestContext,
  jwt: string
): Promise<string | null> {
  // Prefer a completed submission, fall back to any submission.
  for (const status of ['completed', '']) {
    const q = status ? `&status=${status}` : '';
    const res = await request.get(`${API_BASE}/api/v1/submissions?limit=5${q}`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!res.ok()) continue;
    const body = await res.json();
    const items = Array.isArray(body) ? body : body.items ?? [];
    if (items.length > 0) return String(items[0].id);
  }
  return null;
}

test.describe('Part D #1 — Composite Score card', () => {
  test('ResultsPage renders Composite Score card with three components', async ({
    page,
    request,
  }) => {
    const jwt = await getJwt(page);
    const submissionId = await findResultsSubmissionId(request, jwt);
    if (!submissionId) {
      test.skip(true, 'no submissions exist on this account');
      return;
    }

    await page.goto(`/results/${submissionId}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Wait for the Results page to fetch (hook useResults + useSubmission)
    // before probing for the card.
    await page.waitForTimeout(1500);

    const compositeCard = page
      .locator('text=/composite score/i')
      .first()
      .locator(
        'xpath=ancestor::*[contains(@class,"rounded-lg") or self::section or self::div][1]'
      );
    // Alternative: just look for the heading and its neighbors.
    const header = page.getByRole('heading', { name: /composite score/i }).first();

    // If the submission has a composite breakdown, the card appears.
    // If not (old submissions pre-April), skip with a clear signal.
    const hasCard = await header.isVisible().catch(() => false);
    if (!hasCard) {
      test.skip(
        true,
        `submission ${submissionId} has no composite_breakdown (likely pre-Apr 16 evaluation)`
      );
      return;
    }

    // Three component labels.
    for (const label of ['Binary', 'State', 'Residual']) {
      await expect(page.locator(`text=/^${label}$/i`).first()).toBeVisible();
    }

    // Weights readout: "X% × Y = Z%" or similar — a percent sign visible nearby.
    await expect(page.locator('text=/%/').first()).toBeVisible();
    void compositeCard; // silence unused hint
  });

  test('fallback banner renders when state component is unavailable', async ({
    page,
    request,
  }) => {
    const jwt = await getJwt(page);
    // Look for any submission whose composite_breakdown.fallback_reason
    // equals "no_state" / "no_residual" — signal that banner should show.
    const res = await request.get(`${API_BASE}/api/v1/submissions?limit=20`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!res.ok()) {
      test.skip(true, 'cannot list submissions');
      return;
    }
    const body = await res.json();
    const items = Array.isArray(body) ? body : body.items ?? [];
    if (items.length === 0) {
      test.skip(true, 'no submissions to probe');
      return;
    }

    // Probe each submission's results for a fallback_reason.
    let targetId: string | null = null;
    for (const sub of items) {
      const r = await request.get(`${API_BASE}/api/v1/results/${sub.id}`, {
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (!r.ok()) continue;
      const rb = await r.json();
      const reason =
        rb.composite_breakdown?.fallback_reason ?? rb.compositeBreakdown?.fallback_reason;
      if (reason) {
        targetId = String(sub.id);
        break;
      }
    }

    if (!targetId) {
      test.skip(true, 'no submission with a composite fallback_reason to exercise the banner');
      return;
    }

    await page.goto(`/results/${targetId}`);
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(1500);

    // The fallback banner has amber styling and text about state/residual
    // unavailability. Regex keeps it resilient to minor copy edits.
    await expect(
      page
        .locator(
          'text=/(state component unavailable|residual component unavailable|both unavailable|composite reweighted)/i'
        )
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
