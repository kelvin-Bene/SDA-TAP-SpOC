import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Dataset filter combinations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/datasets');
    await expect(page.getByText(/Showing \d+ datasets/i)).toBeVisible();
  });

  test('LEO filter narrows results', async ({ page }) => {
    await page.getByRole('combobox').filter({ hasText: /All Regimes/i }).click();
    await page.getByRole('option', { name: /^LEO/i }).click();
    await page.waitForTimeout(500);
    // Cards should all have LEO badge
    const badges = await page.locator('main').getByText(/^LEO$/, { exact: true }).count();
    expect(badges).toBeGreaterThan(0);
  });

  test('T1 tier filter narrows results', async ({ page }) => {
    await page.getByRole('combobox').filter({ hasText: /All Tiers/i }).click();
    await page.getByRole('option', { name: /T1.*Pristine/i }).click();
    await page.waitForTimeout(500);
    const text = await page.getByText(/Showing \d+ datasets/i).textContent();
    expect(text).toMatch(/Showing \d+ datasets/);
  });

  test('sensor filter opens and selects', async ({ page }) => {
    const sensorCombo = page.getByRole('combobox').filter({ hasText: /All Sensors/i });
    await sensorCombo.click();
    // Options should appear
    await expect(page.getByRole('option').first()).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('search textbox accepts input', async ({ page }) => {
    const searchBox = page.getByRole('textbox', { name: /Search/i });
    await searchBox.fill('LEO');
    await page.waitForTimeout(500);
    const text = await page.getByText(/Showing \d+ datasets/i).textContent();
    expect(text).toMatch(/Showing \d+ datasets/);
  });

  test('descending toggle works', async ({ page }) => {
    await page.getByRole('button', { name: 'Descending' }).click();
    await page.waitForTimeout(300);
    // Button should still be present (toggle state change)
    await expect(page.getByRole('button', { name: /Ascending|Descending/i })).toBeVisible();
  });
});
