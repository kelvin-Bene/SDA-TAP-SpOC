# Comprehensive Production QA Run — 2026-04-17

**Target:** `https://frontend-production-6d80.up.railway.app` + `https://backend-production-4b02.up.railway.app`
**Operator:** kelvin@thebenedicts.net (test account)
**Tool:** Playwright (existing prod suite + supplementary spec `91-supplementary.spec.ts`)
**Scope:** Every route, feature, and user flow. Desktop (1280×800) + Mobile Safari (375×667).
**Deploy under test:** `/assets/index-DeBCRWm4.js` / `/assets/index-B28a6HrB.css` — built 2026-04-17 14:28:58 UTC.

## TL;DR

- **65/82 existing prod specs passed, 2 failed (flaky timeouts), 15 skipped (mostly due to missing test data — which itself is a symptom of the critical bug).**
- **8/10 supplementary specs passed; 2 failed, both encoding real production regressions.**
- **🔴 One CRITICAL demo blocker found:** the entire evaluation pipeline is broken — **11/11 submissions on the test account have `status=failed`**, leaderboard has **0 entries**, nothing completes end-to-end.
- **🟠 One HIGH-severity data-plumbing bug found:** `submission.error_message` is NULL even when the underlying job has a populated `error` — the UI falls back to generic banner copy.

---

## 🔴 CRITICAL — Demo blockers

### C1. Evaluation pipeline fails on every post-Apr-9 dataset (missing reference state vectors)

**Observed:** Every submission on the test account (IDs 9–19) is `status=failed`. All submitted against datasets ≥ 2026-04-14.
**Expected:** At least one completed submission; a populated leaderboard.
**Root cause (from `/api/v1/jobs/{id}`):**
```
ValueError: Dataset 158 has no reference state vectors persisted.
Re-generate the dataset with the post-Phase-1 worker before evaluating,
or ask an admin to backfill dataset_references.
```
**File:lines:**
- `frontend/src/pages/SubmitPage.tsx:73-80` — filter is DATE-ONLY (`createdAt >= 2026-04-09`), does not check reference-orbit existence.
- `backend_api/jobs/workers.py` (evaluation worker) — raises ValueError before populating `submission.error_message`.

**Repro:**
1. Log in as `kelvin@thebenedicts.net`.
2. Go to `/submit`.
3. Select any Apr-14+ dataset from the dropdown (e.g. `LEO-standard-2026-04-14-…-60b847b9`).
4. Upload any valid UCTP JSON.
5. Submit → navigate to `/submit/my-submissions` → status flips to `failed` within ~5s.

**Evidence:**
```
submissions status breakdown: { failed: 11 }
```
All 11 submissions target dataset 158 (or 153, which also has no reference state vectors even though it IS the owner-test dataset).

**Regression link:** Related to the commit `f2fdd50` batch that added the `EVAL_CUTOFF_MS` filter. Filter should be expanded to include an existence-of-reference check (client-side from `/datasets/{id}/reference-orbits` or server-side `/datasets?has_refs=true`), OR the data backfill from `BACKLOG.md Section D` must be completed before the demo.

**Impact:** The platform cannot show a working end-to-end flow. Louis demo will have an empty leaderboard and every live submission demoed will fail.

**Suggested fix path:**
- Short term (pre-demo): backfill `dataset_references` for at least one Apr-14+ dataset so one working submission exists, then exclude the rest from Submit dropdown until the backfill completes.
- Medium term: change `SubmitPage.tsx:78-80` filter to require `d.hasReferenceOrbits === true` (add the boolean to `/datasets/` payload), or switch to server-side filtering via a new `?eval_ready=true` query param.

---

## 🟠 HIGH — Regression on recent change

### H1. `submission.error_message` is NULL on failed submissions (job.error not propagated)

**Observed:** `GET /api/v1/submissions/19` returns `error_message: null` even though the corresponding job has:
```
error: "ValueError: Dataset 158 has no reference state vectors persisted..."
```
**Expected:** `submission.error_message` should carry the first line of `job.error` so ResultsPage can show actionable copy instead of generic "evaluation pipeline encountered an error".

**File:lines:** `backend_api/routers/submissions.py` (wherever job → submission status updates happen) OR the worker finalization step in `backend_api/jobs/workers.py`. The write-back on job failure is not persisting `error_message` to the submission row.

**Repro:**
1. `curl -H "Authorization: Bearer $JWT" $BE/api/v1/submissions/19` → `error_message: null`.
2. `curl -H "Authorization: Bearer $JWT" $BE/api/v1/jobs/e1b21f57-cb4f-4bea-baa1-0506eac08a3b` → `error: "ValueError: Dataset 158…"`.

**UI impact:** ResultsPage banner currently says *"Evaluation Failed — The evaluation pipeline encountered an error. Metrics below are not meaningful."* (captured by the supplementary spec at line 304). That's the fallback copy when `error_message` is null. The real reason (missing reference state vectors → actionable: re-generate dataset) is hidden from the user.

**Regression link:** This is the B2 "evaluation-failed banner" feature from `f2fdd50`. The spec `41-results-failed.spec.ts` only asserts the banner's presence, not that it surfaces actionable copy, so the regression slipped through.

**Suggested fix:** in the job-finalization callback, set `submission.error_message = str(exc)` (first line) on the failure path. Add a spec assertion: `expect(sub.error_message).toMatch(/reference state vectors|dataset|evaluation/i)`.

---

## 🟡 MEDIUM — Flaky/coverage findings

### M1. `11-navigation.spec.ts › /docs renders` timed out (30s) on desktop-auth
- Page rendered correctly per the capture (`test-results\prod-11-navigation-.../test-failed-1.png` shows "Documentation" + "Getting Started" fully loaded).
- 30s test timeout too tight for cold-start of /docs on desktop (mobile-safari-auth `/docs renders with no horizontal overflow` passed in 6.9s).
- **Suggested fix:** bump the test-level timeout on this single test to 45_000 (uses `test.setTimeout(45_000)` inside the test, or tighten the spinner-wait to `Promise.race` with the content check).

### M2. `20-datasets-browse.spec.ts › search input accepts text` timed out in beforeEach (30s)
- Same cold-start flake pattern — `page.goto('/datasets')` took too long.
- **Suggested fix:** add `test.slow()` at `describe` scope, or relax the `beforeEach` to not `await` `#root` explicitly (React hydrates quickly, the 15s timeout is generous enough).

### M3. Leaderboard tooltip test is skipped on mobile + desktop
- `50-leaderboard.spec.ts:37` needs a `cursor-help`/`border-dotted` span in a leaderboard row to trigger hover.
- With **zero** leaderboard entries (symptom of C1), the selector finds nothing → skip.
- Not a spec bug; it's downstream of C1. Once C1 is fixed (one completed submission → one leaderboard row), this test will exercise the tooltip.

### M4. Composite-score card tests skipped (desktop-auth + mobile-safari-auth)
- `40-results-composite.spec.ts:54` and `40-results-composite.spec.ts:102` skip when no submission has a populated `composite_breakdown`.
- Downstream of C1 — every submission is failed → no composite scores → no breakdowns to assert on.

### M5. Dataset generator spec skipped (`24-generator.spec.ts:7`)
- Skips because "generator page is reachable from Datasets browser" couldn't find a visible entry link from `/datasets`.
- Confirmed locally: there IS a "Generate Dataset" link in the sidebar (`/datasets/generate`) but the test looks on the `/datasets` page body, not the sidebar.
- **Suggested fix:** broaden the selector to include sidebar links: `page.locator('a[href="/datasets/generate"]').first()`.

### M6. Non-owner 3D-orbit visibility spec skipped (`60-globe.spec.ts:78`)
- Can't find an "other user's dataset" because the `/api/v1/datasets/` response doesn't include `user_id`/`owner_id` fields. The filter `items.find(d => (d.user_id || d.owner_id))` never matches.
- **Suggested fix:** either add `user_id` to the payload, or change the spec to probe differently (e.g. compare against `/datasets?mine=true` result — any dataset ID NOT in that list is "other user's").

---

## 🟢 Confirmed passing behaviors (explicit regression-check)

All of these worked correctly on the run — encoded for posterity since each was a recent-change risk area:

1. **B1 SubmitPage dropdown filter is active** — spec `30-submit-filter.spec.ts` passed; only post-Apr-9 datasets appear. *(But see C1: filter is incomplete.)*
2. **M5 answer-key separation in Sample Preview** — spec `22-sample-preview.spec.ts` passed; no answer-key fields leak.
3. **M5 answer-key separation in dataset download** — spec `21-datasets-detail.spec.ts:76` passed; 11-field schema only, non-owner gets 403.
4. **Observations endpoint answer-key integrity** — supplementary spec confirmed `id_on_orbit`, `orig_object_id`, `orig_sensor_id` are all null in sample observations (keys exist but never populated).
5. **M6 friendly 404 for unknown datasets** — spec `21-datasets-detail.spec.ts:63` passed.
6. **Composite-score response shape** — supplementary spec confirmed `/leaderboard/` returns the expected envelope (`entries`, `total_entries`, `last_updated`).
7. **Nginx cache headers (deploy visibility fix `236dea0`)** — supplementary spec confirmed:
   - `/` → `no-cache, no-store, must-revalidate`
   - `/assets/index-*.js` → `public, max-age=31536000, immutable`
8. **3D-orbit globe doesn't crash for owner** — spec `60-globe.spec.ts:56` passed.
9. **Orbits tab switching on ResultsPage doesn't throw** — spec `42-results-orbits.spec.ts:84` passed (Cesium React #31 fix holds).
10. **Settings page doesn't leak credential plaintext** — spec `70-profile-settings.spec.ts:17` passed.
11. **iPhone SE mobile parity (no horizontal overflow)** on `/dashboard`, `/datasets`, `/submit`, `/leaderboard`, `/docs`, `/profile`, `/settings` — all passed.
12. **Hamburger menu opens drawer on mobile** — `90-mobile-parity.spec.ts:37` passed.
13. **Health + auth endpoints return expected status** — `99-api-smoke.spec.ts` passed: `/health` reports `orekit: available`, `/api/v1/datasets` returns 401 unauth'd.
14. **Evaluation-failed banner renders** — `41-results-failed.spec.ts` passed; dimmed grid (`opacity-40`) also visible. *(But see H1: banner copy is generic, not actionable.)*
15. **/auth/me returns profile with UDL token redacted** — `udl_token: "****biE="` (last 4 chars only).

---

## 🔵 LOW — Minor observations

- **L1. Window Selection backend attribute error persists in dataset metadata.** `dataset.performance_metadata["Window Selection Metadata"]` for dataset 158 contains `{"error":"'WindowEvaluation' object has no attribute 'avg_orbital_coverage'","status":"failed"}`. Cosmetic — doesn't block evaluation, but it means the dataset-generation pipeline is also partially broken. Worth filing separately.
- **L2. Dataset 153 (owner-test, pre-Apr-9) returns empty `satellites: []` on `/reference-orbits`.** Consistent with C1 — this dataset was created before the Phase-1 reference-persistence worker shipped. Expected.
- **L3. `total_submissions: 0` in `/leaderboard/statistics` despite 11 failed submissions existing.** Stats endpoint likely only counts completed submissions — confirm that's intentional copy/math, not a bug.
- **L4. Job cleanup.** `/api/v1/jobs/` returned only 1 job although 11+ submissions failed. Old jobs are being purged — verify retention policy is intentional before demo day so we don't lose forensic ability.
- **L5. Feedback endpoint.** `/api/v1/feedback` returns `403 Admin access required` for regular users — confirm this matches intent (users can POST feedback but not GET list?). No UX issue observed, but API semantics are asymmetric.

---

## Summary matrix

| Severity | Count | Names |
|---|---|---|
| 🔴 Critical | 1 | C1 evaluation pipeline broken end-to-end |
| 🟠 High | 1 | H1 error_message not propagated |
| 🟡 Medium | 6 | M1 flake, M2 flake, M3/M4 downstream of C1, M5 selector gap, M6 data gap |
| 🔵 Low | 5 | L1 Window attr error, L2 empty owner refs, L3 stats math, L4 job retention, L5 feedback semantics |

## Artifacts

- **Existing prod suite log:** `C:\Users\kelvi\AppData\Local\Temp\claude\…\tasks\b5hf29p7c.output`
- **Supplementary spec:** `UCT-Benchmark-DMR/combined/frontend/e2e/prod/91-supplementary.spec.ts` (committable; encodes C1 + H1 as CI guardrails going forward)
- **Supplementary run log:** `/tmp/supplementary.log`
- **Failure screenshots:** `UCT-Benchmark-DMR/combined/frontend/test-results/prod-91-supplementary-*/`

## Recommended pre-demo action order

1. **Fix C1 first** — without it, no other improvements matter for Louis's demo.
   - Option A (fastest): backfill `dataset_references` for dataset 158 so one submission completes and populates the leaderboard.
   - Option B (most correct): extend `SubmitPage.tsx:78-80` filter with an eval-readiness check (requires a boolean on `/datasets/` payload).
2. **Fix H1** — a one-line write-back on job failure. Boosts the demo story ("look, when things fail, the user knows why").
3. **Fix M1/M2 flakes** — small test-timeout bumps; prevents CI noise.
4. **(After C1) re-run the full prod suite** — expect M3/M4 to un-skip and produce real assertions on the composite-score card.
5. **File L1** as a separate ticket for post-demo.
