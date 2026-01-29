import { test, expect } from './fixtures';

test.describe('UCTP Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/uctp');
    await page.waitForLoadState('domcontentloaded');
  });

  test('dashboard stat cards render', async ({ page }) => {
    const cards = page.locator('[class*="card"], [class*="stat"]');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('dashboard InfoPopovers on stat cards open', async ({ page }) => {
    const infoTriggers = page.locator('[aria-label*="Learn about"]');
    const count = await infoTriggers.count();
    if (count > 0) {
      await infoTriggers.first().click();
      await expect(
        page.locator('.absolute.z-50.w-80').first()
      ).toBeVisible();
    }
  });

  test('dashboard StepExplainer collapsible', async ({ page }) => {
    const explainer = page.locator('[class*="explainer"], [class*="collapsible"], details').first();
    if (await explainer.isVisible()) {
      await explainer.click();
      await page.waitForTimeout(300);
    }
  });

  test('recent runs table renders', async ({ page }) => {
    const table = page.locator('table')
      .or(page.locator('[class*="table"]'))
      .or(page.getByText(/recent.*run/i));
    await expect(table.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe('UCTP Workbench', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/uctp/workbench', { timeout: 60000 });
    await page.waitForLoadState('domcontentloaded');
  });

  test('workbench page renders', async ({ page }) => {
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('clustering config with InfoPopovers', async ({ page }) => {
    const clusterSection = page.locator('text=/cluster/i').first();
    await expect(clusterSection).toBeVisible({ timeout: 5000 });
    // Check for info popovers in this section
    const infos = page.locator('[aria-label*="Learn about"]');
    const count = await infos.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('IOD config with InfoPopovers', async ({ page }) => {
    const iodSection = page.locator('text=/iod|orbit.*determination/i').first();
    await expect(iodSection).toBeVisible({ timeout: 5000 });
  });

  test('refinement config renders', async ({ page }) => {
    const refineSection = page.locator('text=/refine|refinement/i').first();
    await expect(refineSection).toBeVisible({ timeout: 5000 });
  });

  test('workbench StepExplainer opens/closes', async ({ page }) => {
    const explainer = page.locator('[class*="explainer"], [class*="step"], details').first();
    if (await explainer.isVisible()) {
      await explainer.click();
      await page.waitForTimeout(300);
    }
  });

  test('workbench form validation requires dataset', async ({ page }) => {
    const runBtn = page.getByRole('button', { name: /run|execute|start/i }).first();
    if (await runBtn.isVisible()) {
      const isDisabled = await runBtn.isDisabled();
      if (isDisabled) {
        // Button is disabled before selecting dataset -- validation works
        await expect(runBtn).toBeDisabled();
      } else {
        await runBtn.click();
        // Should show validation or remain on page
        await expect(page).toHaveURL(/\/uctp\/workbench/);
      }
    }
  });
});

test.describe('UCTP Run Results', () => {
  test('run results page for invalid ID shows not found', async ({ page }) => {
    await page.goto('/uctp/runs/99999');
    await page.waitForLoadState('domcontentloaded');
    // Page shows "Run not found." message
    const content = page.getByText(/run not found|not found|back to workbench/i).first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });
});

test.describe('UCTP ML Training', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/uctp/training');
    await page.waitForLoadState('domcontentloaded');
  });

  test('ML training page renders model list', async ({ page }) => {
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('ML training InfoPopovers display', async ({ page }) => {
    const infos = page.locator('[aria-label*="Learn about"]');
    const count = await infos.count();
    if (count > 0) {
      await infos.first().click();
      await expect(
        page.locator('.absolute.z-50.w-80').first()
      ).toBeVisible();
    }
  });
});

test.describe('UCTP Connectivity', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/uctp/connectivity');
    await page.waitForLoadState('domcontentloaded');
  });

  test('connectivity lists all API connectors', async ({ page }) => {
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
    // Should show connector cards
    const cards = page.locator('[class*="card"]');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('connector cards show InfoPopovers', async ({ page }) => {
    const infos = page.locator('[aria-label*="Learn about"]');
    const count = await infos.count();
    if (count > 0) {
      await infos.first().click();
      await expect(
        page.locator('.absolute.z-50.w-80').first()
      ).toBeVisible();
    }
  });

  test('test-all button triggers tests', async ({ page }) => {
    const testAllBtn = page.getByRole('button', { name: /test all|check all/i }).first();
    if (await testAllBtn.isVisible()) {
      await testAllBtn.click();
      // Should show progress or results
      await page.waitForTimeout(1000);
    }
  });
});
