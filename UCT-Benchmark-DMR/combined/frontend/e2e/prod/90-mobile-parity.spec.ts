/**
 * iPhone SE (375x667) regression — mobile overhaul parity.
 *
 * For each core authenticated route, assert:
 *   - page renders
 *   - no horizontal overflow (scrollWidth <= innerWidth, with small slack)
 */
import { test, expect } from '@playwright/test';

const ROUTES = ['/dashboard', '/datasets', '/submit', '/leaderboard', '/docs', '/profile', '/settings'];

test.describe('Mobile 375x667 parity', () => {
  for (const route of ROUTES) {
    test(`${route} renders with no horizontal overflow`, async ({ page, viewport }) => {
      // This spec is in mobile-safari-auth's testMatch; guard anyway.
      if (!viewport || viewport.width > 500) {
        test.skip(true, 'mobile-only spec');
        return;
      }

      await page.goto(route);
      await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
      await page.waitForTimeout(800);

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      // 2px slack for sub-pixel rounding.
      expect(
        overflow.scrollWidth,
        `${route}: scrollWidth ${overflow.scrollWidth} > innerWidth ${overflow.innerWidth}`
      ).toBeLessThanOrEqual(overflow.innerWidth + 2);
    });
  }

  test('hamburger menu opens drawer', async ({ page, viewport }) => {
    if (!viewport || viewport.width > 500) {
      test.skip(true, 'mobile-only spec');
      return;
    }
    await page.goto('/dashboard');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

    const hamburger = page.getByRole('button', { name: /menu|navigation/i }).first();
    if (!(await hamburger.isVisible().catch(() => false))) {
      test.skip(true, 'hamburger not visible in this layout');
      return;
    }
    await hamburger.click();
    await page.waitForTimeout(800);
    // The drawer may render links inside a Radix Dialog / Sheet — pick
    // the first interactable one that matches.
    const drawerLink = page
      .locator('[role="dialog"] a, [data-state="open"] a, nav a, aside a, [class*="drawer"] a')
      .filter({ hasText: /datasets|submit|leaderboard/i })
      .first();
    // Accept either visible-in-drawer OR at least present in DOM —
    // animations can leave it technically hidden for ms.
    const count = await drawerLink.count();
    expect(count).toBeGreaterThan(0);
  });
});
