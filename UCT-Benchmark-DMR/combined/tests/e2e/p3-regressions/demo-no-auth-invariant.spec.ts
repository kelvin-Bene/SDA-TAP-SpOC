import { test, expect } from '../fixtures/consoleWatcher';
import { assertNoAuthState } from '../helpers/navigation';

/**
 * CRITICAL user constraint: demo branch must NEVER require auth or API keys.
 * This sweeps every protected route and verifies no login redirect, no supabase
 * calls, no auth tokens stored anywhere.
 */
const PROTECTED_ROUTES = [
  '/dashboard',
  '/datasets',
  '/datasets/generate',
  '/datasets/my-datasets',
  '/datasets/1',
  '/submit',
  '/submit/my-submissions',
  '/results/8',
  '/leaderboard',
  '/profile',
  '/settings',
];

test.describe('P3 Regression — Demo no-auth invariant (CRITICAL)', () => {
  // This suite iterates 11 routes; give it extra time under Railway CDN load
  test.slow();

  // Ensure auto-login is NOT suppressed by a stray demo_logged_out flag from another test
  test.beforeEach(async ({ context }) => {
    await context.addInitScript(() => {
      try { sessionStorage.removeItem('demo_logged_out'); } catch { /* ignore */ }
    });
  });

  test('no supabase requests across full route sweep', async ({ page }) => {
    const supabaseHits: string[] = [];
    page.on('request', (req) => {
      if (/supabase\.co/.test(req.url())) supabaseHits.push(req.url());
    });
    for (const route of PROTECTED_ROUTES) {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
    }
    expect(supabaseHits, 'Demo mode MUST NOT call supabase on any route').toEqual([]);
  });

  test('no route redirects to /login or /welcome', async ({ page }) => {
    for (const route of PROTECTED_ROUTES) {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
      expect(
        page.url(),
        `Route ${route} must not redirect to auth`,
      ).not.toMatch(/\/login|\/welcome|\/signin/);
    }
  });

  test('no auth state persists after visiting every route', async ({ page }) => {
    for (const route of PROTECTED_ROUTES) {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
    }
    await assertNoAuthState(page);
  });
});
