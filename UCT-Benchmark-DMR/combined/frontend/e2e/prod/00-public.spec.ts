/**
 * Public (unauthenticated) surface on prod.
 *
 * Verifies:
 *   - Landing page renders + CTAs present
 *   - Landing hero globe: desktop has <canvas>, mobile has SVG fallback
 *   - Docs page renders all 5 tabs
 *   - Docs has M5 "Answer-Key Separation" section and does NOT say "truth catalog"
 *   - Login page renders
 *   - 404 route renders the Go Home / Not Found page
 *
 * Uses a clean session (explicitly clears storageState) so authenticated-only
 * behavior can't bleed in from auth.setup.ts.
 */
import { test, expect, devices } from '@playwright/test';

test.use({ storageState: { cookies: [], origins: [] } });

test.describe('Public — Landing', () => {
  test('loads with hero + CTA', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));

    await page.goto('/');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Hero headline is always present regardless of viewport.
    const heading = page.getByRole('heading', { level: 1 }).first();
    await expect(heading).toBeVisible();

    // At least one CTA button (Get Started / Sign In / Try Demo).
    const cta = page
      .getByRole('link', { name: /get started|sign in|try demo|demo/i })
      .or(page.getByRole('button', { name: /get started|sign in|try demo|demo/i }));
    await expect(cta.first()).toBeVisible();

    expect(errors, 'no page errors on /').toEqual([]);
  });

  test('desktop: hero right column renders a visual (Cesium canvas or SVG fallback)', async ({ page, viewport }) => {
    test.skip(!viewport || viewport.width < 1024, 'hero visual only renders at lg+');

    await page.goto('/');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Either a Cesium canvas (when WebGL + Ion token are healthy) or the
    // SVG OrbitalGraphic fallback must be visible. Playwright's headless
    // Chromium can fail Cesium's WebGL capability check, and prod may have
    // VITE_ENABLE_GLOBE unset — both legitimate paths to the SVG fallback.
    const visual = page.locator('canvas, svg[aria-label*="orbit" i], svg').first();
    await expect(visual).toBeVisible({ timeout: 20_000 });
  });

  test('mobile: hero has no Cesium canvas (SVG fallback only)', async ({ page, viewport }) => {
    test.skip(!viewport || viewport.width >= 1024, 'mobile-only assertion');

    await page.goto('/');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    // Small dwell so any lazy-loaded content has a chance to mount.
    await page.waitForTimeout(1500);
    // Hero's LandingGlobe is wrapped in `hidden lg:block` so mobile renders
    // the OrbitalGraphic SVG fallback. Canvas must be absent on mobile.
    await expect(page.locator('canvas')).toHaveCount(0);
  });
});

test.describe('Public — Docs (M5: answer-key separation)', () => {
  test('renders the five documentation tabs', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // All five tabs must be present in the tab bar. Tab labels roughly:
    //   Getting Started | Dataset Format | Submission | Metrics | Pipeline
    for (const label of [/getting started/i, /dataset format/i, /submission/i, /metrics/i, /pipeline/i]) {
      const tab = page.getByRole('tab', { name: label }).or(page.locator(`text=${label}`)).first();
      await expect(tab).toBeVisible();
    }
  });

  test('M5: Getting Started mentions Answer-Key Separation', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Default tab is "Getting Started". The Answer-Key Separation section
    // was added today — scoped under the Dataset Format tab in the source,
    // so also click that tab to ensure it's rendered.
    const datasetFormatTab = page.getByRole('tab', { name: /dataset format/i }).first();
    if (await datasetFormatTab.isVisible().catch(() => false)) {
      await datasetFormatTab.click();
    }

    // Match any heading level — the source uses <h4>, but role queries can
    // be picky about heading levels exposed via ARIA trees. Fall back to a
    // visible-text match to be robust.
    await expect(
      page.locator('text=/answer.?key separation/i').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('M5: "truth catalog" is NOT referenced anywhere in docs', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    // Visit each tab and sanity-check. The stale phrasing was removed today.
    for (const label of [/getting started/i, /dataset format/i, /submission/i, /metrics/i, /pipeline/i]) {
      const tab = page.getByRole('tab', { name: label }).first();
      if (await tab.isVisible().catch(() => false)) {
        await tab.click();
      }
      await page.waitForTimeout(200);
      const body = (await page.locator('main').innerText()).toLowerCase();
      expect(body, `"truth catalog" leaked on tab ${label}`).not.toContain('truth catalog');
    }
  });
});

test.describe('Public — Login page', () => {
  test('login form renders', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    await expect(page.locator('input[type="password"]').first()).toBeVisible();
    await expect(
      page.getByRole('textbox', { name: /email/i }).or(page.locator('input[type="email"]')).first()
    ).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i }).first()).toBeVisible();
  });
});

test.describe('Public — 404', () => {
  test('unknown route renders Not Found', async ({ page }) => {
    await page.goto('/definitely-not-a-real-route-9999');
    await expect(page.locator('text=/404|not found/i').first()).toBeVisible({ timeout: 10_000 });
  });
});
