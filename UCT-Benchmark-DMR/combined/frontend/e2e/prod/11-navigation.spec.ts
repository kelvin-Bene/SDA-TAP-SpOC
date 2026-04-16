/**
 * Sidebar / header navigation — links land on the expected pages.
 */
import { test, expect } from '@playwright/test';

async function gotoAndSettle(page: import('@playwright/test').Page, url: string) {
  await page.goto(url);
  await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
}

test.describe('Navigation (authenticated)', () => {
  const routes: Array<[string, RegExp]> = [
    ['/dashboard', /dashboard|good to see you/i],
    ['/datasets', /datasets/i],
    ['/datasets/my-datasets', /datasets|my datasets/i],
    ['/submit', /submit|upload/i],
    ['/submit/my-submissions', /submissions|my submissions/i],
    ['/leaderboard', /leaderboard|rank/i],
    ['/profile', /profile/i],
    ['/settings', /settings|credentials/i],
    ['/docs', /documentation|getting started/i],
  ];

  for (const [url, expected] of routes) {
    test(`${url} renders`, async ({ page }) => {
      await gotoAndSettle(page, url);
      await expect(page.locator('body')).toContainText(expected, { timeout: 10_000 });
    });
  }
});
