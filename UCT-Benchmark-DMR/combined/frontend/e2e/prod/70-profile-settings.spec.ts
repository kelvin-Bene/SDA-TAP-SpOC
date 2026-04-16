/**
 * Profile + Settings pages render and do not leak credential plaintexts.
 */
import { test, expect } from '@playwright/test';

test.describe('Profile page', () => {
  test('renders user identity', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await expect(
      page.locator('text=/profile|email|member since/i').first()
    ).toBeVisible({ timeout: 10_000 });
  });
});

test.describe('Settings page', () => {
  test('Credentials section renders without leaking plaintext', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
    await expect(
      page.locator('text=/credential|udl|esa|api/i').first()
    ).toBeVisible({ timeout: 10_000 });

    // Credential values should NEVER appear plaintext — look for a bunch of
    // asterisks or "not configured" instead.
    const body = await page.locator('body').innerText();
    // If any credential inputs are on the page, they should be type=password.
    const plainTextInputs = await page.locator('input[type="text"][name*="token" i]').count();
    expect(plainTextInputs, 'credential token inputs must not be plaintext type').toBe(0);
    // Safety belt: the body shouldn't contain a known JWT prefix.
    expect(body).not.toMatch(/eyJhbGciOiJ/);
  });
});
