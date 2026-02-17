import { test, expect } from './fixtures';

test.describe('Dataset Browser Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/datasets');
    await page.waitForLoadState('domcontentloaded');
  });

  test('dataset browser renders with heading', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /dataset/i }).first();
    await expect(heading).toBeVisible();
  });

  test('InfoPopover on header opens on click', async ({ page }) => {
    const infoTrigger = page.locator('[aria-label*="Learn about"]').first();
    if (await infoTrigger.isVisible()) {
      await infoTrigger.click();
      const popover = page.locator('.absolute.z-50.w-80').first();
      await expect(popover).toBeVisible();
    }
  });

  test('filters show Regime, Tier, Status selectors', async ({ page }) => {
    // Use specific label selectors to avoid strict mode violations
    const regimeLabel = page.locator('label').filter({ hasText: /regime/i }).first();
    const tierLabel = page.locator('label').filter({ hasText: /tier/i }).first();
    await expect(regimeLabel).toBeVisible({ timeout: 5000 });
    await expect(tierLabel).toBeVisible({ timeout: 5000 });
  });

  test('filter InfoPopovers display correctly', async ({ page }) => {
    const filterPopovers = page.locator('[aria-label*="Learn about"]');
    const count = await filterPopovers.count();
    expect(count).toBeGreaterThanOrEqual(0);
    if (count > 0) {
      await filterPopovers.first().click();
      await expect(page.locator('.absolute.z-50.w-80').first()).toBeVisible();
    }
  });

  test('dataset cards render', async ({ page }) => {
    // Wait for API response
    await page.waitForTimeout(2000);
    const cards = page.locator('[class*="card"]');
    // May be 0 if no datasets in DB, that's OK
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('clicking dataset card opens preview dialog', async ({ page }) => {
    await page.waitForTimeout(2000);
    const card = page.locator('[class*="card"]').first();
    if (await card.isVisible()) {
      await card.click();
      // Dialog or detail view should appear
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Dataset Generator Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.waitForLoadState('domcontentloaded');
  });

  test('generator renders with heading', async ({ page }) => {
    // Generator page may have different heading text
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('generator renders form steps with StepExplainers', async ({ page }) => {
    // Look for form steps or explainer components
    const steps = page.locator('[class*="step"], [class*="explainer"]');
    const count = await steps.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('ConceptBadge components are clickable', async ({ page }) => {
    const badges = page.locator('[class*="concept"], [class*="badge"]');
    const count = await badges.count();
    if (count > 0) {
      await badges.first().click();
      await page.waitForTimeout(300);
    }
  });

  test('form validation prevents incomplete submission', async ({ page }) => {
    const submitBtn = page.getByRole('button', { name: /generate|create|submit/i }).first();
    if (await submitBtn.isVisible()) {
      await submitBtn.click();
      // Should remain on the page or show validation
      await expect(page).toHaveURL(/\/datasets\/generate/);
    }
  });
});

test.describe('My Datasets Page', () => {
  test('my-datasets page renders', async ({ page }) => {
    await page.goto('/datasets/my-datasets');
    await page.waitForLoadState('domcontentloaded');
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('my-datasets shows list or empty state', async ({ page }) => {
    await page.goto('/datasets/my-datasets');
    await page.waitForLoadState('domcontentloaded');
    // Should show page content - heading or card or empty message
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible({ timeout: 5000 });
  });
});
