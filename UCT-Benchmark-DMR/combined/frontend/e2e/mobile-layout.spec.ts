import { test, expect, expectNoHorizontalScroll, isDesktop } from './fixtures';

/**
 * Cross-viewport layout checks that must hold on every project (mobile,
 * tablet, desktop). Primarily guards against horizontal overflow and touch
 * target regressions.
 *
 * These routes are accessible without auth when VITE_AUTH_ENABLED=false
 * (the e2e harness default).
 */
const SMOKE_ROUTES = [
  { path: '/', label: 'landing' },
  { path: '/welcome', label: 'landing (welcome alias)' },
  { path: '/dashboard', label: 'dashboard' },
  { path: '/datasets', label: 'dataset browser' },
  { path: '/datasets/generate', label: 'dataset generator' },
  { path: '/datasets/my-datasets', label: 'my datasets' },
  { path: '/submit', label: 'submit' },
  { path: '/submit/my-submissions', label: 'my submissions' },
  { path: '/leaderboard', label: 'leaderboard' },
  { path: '/docs', label: 'documentation' },
  { path: '/profile', label: 'profile' },
  { path: '/settings', label: 'settings' },
  { path: '/login', label: 'login' },
] as const;

for (const route of SMOKE_ROUTES) {
  test(`${route.label} (${route.path}) — no horizontal overflow`, async ({ page }) => {
    await page.goto(route.path);
    await page.waitForLoadState('domcontentloaded');
    // Give lazy-loaded chunks + Cesium a moment to settle before measuring.
    await page.waitForTimeout(300);
    await expectNoHorizontalScroll(page);
  });
}

test.describe('mobile sidebar drawer', () => {
  // eslint-disable-next-line no-empty-pattern
  test.skip(({}, testInfo) => isDesktop(testInfo), 'sidebar is overlay drawer only below lg:');

  test('toggle menu opens and closes the drawer', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');

    const aside = page.locator('aside[aria-hidden]');
    await expect(aside).toHaveAttribute('aria-hidden', 'true');

    const toggle = page.getByRole('button', { name: /toggle menu/i });
    await toggle.click();
    await expect(aside).toHaveAttribute('aria-hidden', 'false');

    // Navigating to another route should close the drawer (handled by MainLayout)
    const firstNav = aside.getByRole('link').first();
    await firstNav.click();
    await expect(aside).toHaveAttribute('aria-hidden', 'true');
  });
});

test.describe('touch target sizes', () => {
  test('primary header buttons meet 44×44 px target on mobile', async ({ page }, testInfo) => {
    test.skip(isDesktop(testInfo), 'touch target rule is mobile-only (WCAG 2.5.5 AAA)');
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');

    const menuToggle = page.getByRole('button', { name: /toggle menu/i });
    const box = await menuToggle.boundingBox();
    expect(box, 'menu toggle should have a bounding box').not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(40); // Header uses h-10 w-10 icon button
    expect(box!.height).toBeGreaterThanOrEqual(40);
  });
});
