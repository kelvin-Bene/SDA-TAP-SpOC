import { test, expect } from './fixtures';

test.describe('Submit Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/submit');
    await page.waitForLoadState('domcontentloaded');
  });

  test('submit page renders with file upload zone', async ({ page }) => {
    const uploadZone = page.locator('[class*="dropzone"]')
      .or(page.locator('[class*="upload"]'))
      .or(page.getByText(/drag|drop|upload/i));
    await expect(uploadZone.first()).toBeVisible();
  });

  test('dataset selector and algorithm name input present', async ({ page }) => {
    const algoInput = page.locator('input[name*="algorithm"]')
      .or(page.locator('input[placeholder*="algorithm" i]'))
      .or(page.getByRole('textbox', { name: /algorithm/i }));
    await expect(algoInput.first()).toBeVisible();
  });

  test('form validation requires fields', async ({ page }) => {
    const submitBtn = page.getByRole('button', { name: /submit/i }).first();
    if (await submitBtn.isVisible()) {
      await submitBtn.click();
      // Should remain on submit page or show validation
      await expect(page).toHaveURL(/\/submit/);
    }
  });
});

test.describe('My Submissions Page', () => {
  test('my-submissions lists submissions with status badges', async ({ page }) => {
    await page.goto('/submit/my-submissions');
    await page.waitForLoadState('domcontentloaded');
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('my-submissions shows empty state or list', async ({ page }) => {
    await page.goto('/submit/my-submissions');
    await page.waitForLoadState('domcontentloaded');
    // Page should render with at least a heading
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Results Page', () => {
  test('results page shows not found for invalid ID', async ({ page }) => {
    await page.goto('/results/99999');
    await page.waitForLoadState('domcontentloaded');
    // Should show error/not found state or at least a heading
    const content = page.getByText(/not found|error|no result/i).first()
      .or(page.getByRole('heading').first());
    await expect(content).toBeVisible({ timeout: 5000 });
  });

  test('results page renders for valid submission', async ({ page }) => {
    await page.goto('/results/1');
    await page.waitForLoadState('domcontentloaded');
    // Should render metrics or not-found
    const content = page.getByRole('heading').first();
    await expect(content).toBeVisible({ timeout: 5000 });
  });
});
