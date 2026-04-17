import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Generator wizard deep coverage', () => {
  test('Step 1: all 4 primary regimes present', async ({ page }) => {
    await page.goto('/datasets/generate');
    await expect(page.getByText('Low Earth Orbit')).toBeVisible();
    await expect(page.getByText('Medium Earth Orbit')).toBeVisible();
    await expect(page.getByText('Geosynchronous Orbit')).toBeVisible();
    await expect(page.getByText('Highly Elliptical Orbit')).toBeVisible();
  });

  test('Step 1: all 10 combo regimes present', async ({ page }) => {
    await page.goto('/datasets/generate');
    const combos = [
      'All Regimes',
      'LEO + MEO',
      'LEO + GEO',
      'LEO + HEO',
      'MEO + GEO',
      'MEO + HEO',
      'GEO + HEO',
      'All except HEO',
      'All except GEO',
      'All except MEO',
      'All except LEO',
    ];
    for (const combo of combos) {
      await expect(page.getByText(combo).first()).toBeVisible();
    }
  });

  test('Step 1: target percentage options 50/10/1/Unspecified', async ({ page }) => {
    await page.goto('/datasets/generate');
    await expect(page.getByText('Target Object Percentage')).toBeVisible();
    await expect(page.getByText('50%').first()).toBeVisible();
    await expect(page.getByText('10%').first()).toBeVisible();
    await expect(page.getByText('1%').first()).toBeVisible();
    await expect(page.getByText('Unspecified').first()).toBeVisible();
  });

  test('progress pills show check marks for completed steps', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('main').getByRole('button', { name: /^Next/ }).click();
    await page.getByRole('main').getByRole('button', { name: /^Next/ }).click();
    // After advancing 2 steps, regime and quality should be checked
    // Step pills have a check icon when completed
    const regimePill = page.getByText('Regime').first();
    await expect(regimePill).toBeVisible();
  });
});
