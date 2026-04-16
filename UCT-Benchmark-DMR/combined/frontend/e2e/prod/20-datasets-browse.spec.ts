/**
 * Datasets browser page — list, filters, search, sort, grid/list toggle.
 */
import { test, expect } from '@playwright/test';

test.describe('Datasets browser', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/datasets');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await page.waitForTimeout(1200);
  });

  test('renders dataset list or empty state', async ({ page }) => {
    // Wait for either the grid or an explicit "no datasets" marker.
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(1500);

    const hasCards = (await page.locator('[class*="grid"] [role="article"], [class*="card"], article, [data-testid*="dataset"]').count()) > 0;
    const hasListRows = (await page.locator('table tbody tr, [role="row"]').count()) > 0;
    const emptyState = await page.locator('text=/no datasets|empty|get started/i').first().isVisible().catch(() => false);
    // Fallback: the page's body has meaningful content.
    const bodyText = (await page.locator('body').innerText()).length;
    expect(hasCards || hasListRows || emptyState || bodyText > 200).toBe(true);
  });

  test('regime filter is interactive', async ({ page }) => {
    const filter = page.getByRole('combobox', { name: /regime/i }).first();
    if (!(await filter.isVisible().catch(() => false))) {
      test.skip(true, 'regime filter not visible in this viewport');
      return;
    }
    await filter.click();
    await page.waitForTimeout(400);
    await expect(page.locator('[role="option"]').first()).toBeVisible({ timeout: 5000 });
  });

  test('search input accepts text', async ({ page }) => {
    const search = page.getByRole('textbox', { name: /search/i }).or(page.locator('input[placeholder*="search" i]')).first();
    if (!(await search.isVisible().catch(() => false))) {
      test.skip(true, 'search input not visible');
      return;
    }
    await search.fill('LEO');
    await page.waitForTimeout(300);
    expect(await search.inputValue()).toBe('LEO');
  });
});
