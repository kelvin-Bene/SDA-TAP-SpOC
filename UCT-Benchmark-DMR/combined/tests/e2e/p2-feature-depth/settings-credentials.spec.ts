import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Settings pages', () => {
  test('Service Credentials tab lists UDL/ESA/Orekit', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible();
    await expect(page.getByText(/Unified Data Library \(UDL\)/i)).toBeVisible();
    await expect(page.getByText(/ESA DISCOSweb/i)).toBeVisible();
    await expect(page.getByText(/Orekit Data/i)).toBeVisible();
  });

  test('all credentials show Not Configured in demo mode', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByText(/Unified Data Library/i)).toBeVisible();
    const notConfigured = page.getByText(/Not Configured/i);
    await expect.poll(() => notConfigured.count(), { timeout: 10_000 }).toBeGreaterThanOrEqual(3);
  });

  test('Application tab shows read-only config', async ({ page }) => {
    await page.goto('/settings');
    await page.getByRole('tab', { name: 'Application' }).click();
    await expect(page.getByRole('heading', { name: /Application Configuration/i })).toBeVisible();
    await expect(page.getByText(/API Base URL/i)).toBeVisible();
    await expect(page.getByText(/Auth Status/i)).toBeVisible();
    await expect(page.getByText(/Database Backend/i)).toBeVisible();
  });

  test('Auth Status shows Authenticated in demo', async ({ page }) => {
    await page.goto('/settings');
    await page.getByRole('tab', { name: 'Application' }).click();
    await expect(page.getByText(/Authenticated/i)).toBeVisible();
  });
});
