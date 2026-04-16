import { test, expect, isMobile } from './fixtures';

/**
 * Mobile-specific behavioral tests. These verify that the card-pattern /
 * collapsed-UI variants actually render on mobile viewports and that the
 * layouts don't regress into the desktop flavors.
 */
test.describe('mobile-only page behavior', () => {
  // eslint-disable-next-line no-empty-pattern
  test.skip(({}, testInfo) => !isMobile(testInfo), 'mobile-only tests');

  test('leaderboard renders cards instead of table', async ({ page }) => {
    await page.goto('/leaderboard');
    await page.waitForLoadState('domcontentloaded');

    // Desktop table should be hidden; look for the card list
    const desktopTable = page.locator('.hidden.md\\:block table');
    await expect(desktopTable).toBeHidden();

    // Mobile sort select should exist when there is at least one row
    const hasRows = await page.locator('ul[role="list"] li').count();
    if (hasRows > 0) {
      const sortSelect = page.getByRole('combobox').first();
      await expect(sortSelect).toBeVisible();
    }
  });

  test('dataset generator shows Step X of N text on mobile', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.waitForLoadState('domcontentloaded');

    // Text progress indicator is sm:hidden; mobile sees it
    const stepText = page.getByText(/Step \d+ of \d+/);
    await expect(stepText).toBeVisible();
  });

  test('documentation tabs are horizontally scrollable', async ({ page }) => {
    await page.goto('/docs');
    await page.waitForLoadState('domcontentloaded');

    const tabList = page.getByRole('tablist').first();
    await expect(tabList).toBeVisible();

    const overflows = await tabList.evaluate((el) => el.scrollWidth > el.clientWidth);
    expect(overflows, 'docs tab list should horizontally scroll on mobile').toBe(true);
  });

  test('submit dropzone shows "Tap to choose file" copy', async ({ page }) => {
    await page.goto('/submit');
    await page.waitForLoadState('domcontentloaded');

    // The mobile-only text variant
    const mobileCopy = page.getByText(/tap to choose file/i);
    await expect(mobileCopy).toBeVisible();
  });

  test('leaderboard podium renders #1 at top on mobile', async ({ page }) => {
    await page.goto('/leaderboard');
    await page.waitForLoadState('domcontentloaded');

    const podium = page.locator('text=/#1/').first();
    const podium2 = page.locator('text=/#2/').first();

    // If both exist, #1's box.y should be <= #2's (rendered visually above)
    const hasBoth = (await podium.count()) > 0 && (await podium2.count()) > 0;
    if (hasBoth) {
      const box1 = await podium.boundingBox();
      const box2 = await podium2.boundingBox();
      if (box1 && box2) {
        expect(box1.y, '#1 should render visually above #2 on mobile').toBeLessThanOrEqual(box2.y);
      }
    }
  });
});
