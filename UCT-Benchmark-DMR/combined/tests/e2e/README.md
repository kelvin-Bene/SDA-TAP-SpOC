# E2E Test Suite

Playwright end-to-end tests for the DMR demo (UCT Benchmark Platform).

**Target environment:** Railway live demo at `https://frontend-demo-1542.up.railway.app`  
Override with the `FRONTEND_URL` env var if needed.

## Quick start

```bash
# From this directory
npm install
npx playwright install chromium    # one-time browser download
npm run test:e2e                   # run full suite
```

## Available scripts

| Command | What it runs | Typical time |
|---------|-------------|--------------|
| `npm run test:e2e` | Full suite (all 4 tiers + legacy specs) | ~15-25 min |
| `npm run test:e2e:smoke` | P0 only — gate-keeper checks | ~1 min |
| `npm run test:e2e:core` | P0 + P1 core flows | ~5 min |
| `npm run test:e2e:depth` | P2 feature depth | ~4 min |
| `npm run test:e2e:regress` | P3 regression tests | ~4 min |
| `npm run test:e2e:cesium` | Only Cesium-specific regressions | ~3 min |
| `npm run test:e2e:headed` | Run in visible browser (debug) | varies |
| `npm run test:e2e:ui` | Playwright UI mode (interactive) | interactive |
| `npm run test:e2e:report` | Open last run's HTML report | — |

## Structure

```
tests/e2e/
├── playwright.config.ts         # Config (targets Railway by default)
├── package.json                 # Test scripts + playwright dep
├── fixtures/
│   ├── consoleWatcher.ts        # Shared fixture — fails on CSP/WebGL/uncaught errors
│   ├── valid_submission.json    # Passes all 5 validation steps on /submit
│   ├── invalid_submission.json  # Malformed JSON (format check fails)
│   └── wrong_schema_submission.json
├── helpers/
│   ├── cesium.ts                # waitForCesiumCanvas, assertNoCesiumInfoBox, etc.
│   ├── navigation.ts            # gotoAndHydrate, assertNoAuthState
│   └── viewports.ts             # MOBILE/TABLET/DESKTOP presets
├── p0-smoke/                    # Gate-keeper (app loads, demo auth, CSP header)
├── p1-core-flows/               # Primary user journeys
├── p2-feature-depth/            # Deep tab/filter/modal coverage
└── p3-regressions/              # Specific prevention tests for recent churn
    ├── cesium-csp-*.spec.ts     # Guards commits 377a4b9, 8194c74
    ├── cesium-mount-*.spec.ts   # Guards commit fed4677 (resium bypass)
    ├── no-resium-jsx.spec.ts    # Static guard against resium re-introduction
    ├── demo-no-auth-invariant.spec.ts  # CRITICAL: demo must never require auth
    └── railway-image-freshness.spec.ts # Detects stale Railway image
```

## The console watcher

Every spec imports `test` from `fixtures/consoleWatcher.ts` (not from `@playwright/test` directly). This fixture:
- Captures all console errors, warnings, and uncaught page errors.
- Silently drops a small allowlist (e.g. ion token missing warnings).
- FAILS the test if any CSP violation, WebGL error, chunk-load failure, or React error appears.

To allow an expected noisy error in one test (e.g. 404s on bad IDs):

```typescript
test('bad dataset', async ({ page, consoleWatcher }) => {
  consoleWatcher.allow(/404/);  // or any regex
  await page.goto('/datasets/99999');
  // ...
});
```

## Critical invariants

1. **Demo branch has no auth.** `p3-regressions/demo-no-auth-invariant.spec.ts` verifies no supabase.co network requests fire on any route, no login redirects, no auth tokens in storage/cookies.
2. **Cesium must not regress.** The entire `p3-regressions/cesium-*.spec.ts` suite targets the CSP/resium-bypass commits. Run `npm run test:e2e:cesium` after any Cesium- or CSP-touching change.
3. **Railway image must match git.** `railway-image-freshness.spec.ts` HEADs the live URL and checks the delivered CSP header includes directives from the current `nginx.conf`.

## CI notes

- Workers pinned to 1 on Railway (shared backend; avoids rate-limits)
- Retries: 0 locally, 2 on CI
- Trace captured only on retry to reduce artifact size
- Screenshots captured on failure
- HTML + JSON reports written to `../../playwright-report/`

## Selector gotchas

- **Radix tabs** do NOT respond to `el.click()` inside `page.evaluate()` — they rely on pointer events. Use Playwright's real `.click()` / `browser_click`.
- **Sidebar duplicates** — many link/button labels appear both in sidebar nav and in main content. Scope with `page.getByRole('main')` to disambiguate.
- **Numbers with commas** — e.g. "Showing 20 of 2,450 observations" — regex needs `[\d,]+` not `\d+`.
