import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P1 Core — Generator wizard', () => {
  test('5 wizard steps reachable via Next', async ({ page }) => {
    await page.goto('/datasets/generate');
    await expect(page.getByRole('heading', { name: 'Generate Dataset', level: 1 })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Select Orbital Regime/i })).toBeVisible();

    await page.getByRole('main').getByRole('button', { name: /^Next/ }).click();
    await expect(page.getByRole('heading', { name: /Data Quality Parameters/i })).toBeVisible();

    await page.getByRole('main').getByRole('button', { name: /^Next/ }).click();
    await expect(page.getByRole('heading', { name: /Object Selection/i })).toBeVisible();

    await page.getByRole('main').getByRole('button', { name: /^Next/ }).click();
    await expect(page.getByRole('heading', { name: /Advanced Options/i })).toBeVisible();

    await page.getByRole('main').getByRole('button', { name: /^Next/ }).click();
    await expect(page.getByRole('heading', { name: /Review Configuration/i })).toBeVisible();
    await expect(page.getByRole('main').getByRole('button', { name: /Generate Dataset/i })).toBeVisible();
  });

  test('Legacy Code tab switches and shows 16-char code', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('tab', { name: /Legacy Code/i }).click();
    await expect(page.getByText('Current Dataset Code')).toBeVisible();
    // 16-char code displayed
    await expect(page.getByText(/^[A-Z0-9]{16}$/)).toBeVisible();
  });

  test('Back button preserves wizard state', async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.getByRole('main').getByRole('button', { name: /^Next/ }).click();
    await expect(page.getByRole('heading', { name: /Data Quality/i })).toBeVisible();
    await page.getByRole('main').getByRole('button', { name: /^Back/ }).click();
    await expect(page.getByRole('heading', { name: /Select Orbital Regime/i })).toBeVisible();
  });
});
