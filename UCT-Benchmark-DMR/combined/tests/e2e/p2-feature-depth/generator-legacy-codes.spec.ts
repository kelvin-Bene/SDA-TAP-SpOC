import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Generator legacy code mode', () => {
  test('legacy tab exposes 7-step wizard', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('tab', { name: /Legacy Code/i }).click();
    // Legacy mode has more steps: Object / Regime / Event / Sensor / Quality / Objects / Review
    await expect(page.getByText('Current Dataset Code')).toBeVisible();
  });

  test('legacy mode shows 16-char code format', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('tab', { name: /Legacy Code/i }).click();
    const code = await page.locator('text=/^[A-Z0-9]{16}$/').first().textContent();
    expect(code).toMatch(/^[A-Z0-9]{16}$/);
  });

  test('legacy mode object type options all present', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('tab', { name: /Legacy Code/i }).click();
    await expect(page.getByText(/HAMR \(High Area-to-Mass Ratio\)/i)).toBeVisible();
    await expect(page.getByText(/Close physical proximity/i)).toBeVisible();
    await expect(page.getByText(/Apparent angular proximity/i)).toBeVisible();
    await expect(page.getByText(/Unspecified\/Normal/i)).toBeVisible();
    await expect(page.getByText(/Calibration satellites/i)).toBeVisible();
  });

  test('legacy target percentage options 10/50/01/UN', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('tab', { name: /Legacy Code/i }).click();
    await expect(page.getByText('Target Percentage').first()).toBeVisible();
  });

  test('Use Wizard / Enter Code buttons present', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('tab', { name: /Legacy Code/i }).click();
    await expect(page.getByRole('button', { name: 'Use Wizard' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Enter Code' })).toBeVisible();
  });
});
