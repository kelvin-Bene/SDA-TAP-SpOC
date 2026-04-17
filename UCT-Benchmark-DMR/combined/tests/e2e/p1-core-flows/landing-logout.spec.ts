import { test, expect } from '../fixtures/consoleWatcher';

/**
 * P1 Core — Landing page + logout flow.
 * When logged out, / renders LandingPage with Try Demo + Go to Main buttons.
 * When logged in, / redirects to /dashboard.
 */
test.describe('P1 Core — Landing + logout', () => {
  test('root shows landing page when demo_logged_out flag is set', async ({ page }) => {
    // Flip the flag before the app initializes
    await page.addInitScript(() => {
      sessionStorage.setItem('demo_logged_out', 'true');
    });
    await page.goto('/');
    await expect(page.getByRole('button', { name: /Try Demo/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Go to Main/i }).first()).toBeVisible();
  });

  test('Try Demo returns to /dashboard with Demo User logged in', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('demo_logged_out', 'true');
    });
    await page.goto('/');
    await page.getByRole('button', { name: /Try Demo/i }).first().click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();
    // Flag should be cleared
    const flag = await page.evaluate(() => sessionStorage.getItem('demo_logged_out'));
    expect(flag).toBeNull();
  });

  test('logout from header redirects to production landing URL', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: /Demo User/i, level: 1 })).toBeVisible();

    // Capture the outgoing navigation before it leaves the demo origin
    const navigationPromise = page.waitForRequest(
      /frontend-production-6d80\.up\.railway\.app/,
      { timeout: 10_000 },
    );
    await page.getByRole('button', { name: 'User menu' }).click();
    await page.getByRole('menuitem', { name: /Log out/i }).click();

    const req = await navigationPromise;
    expect(req.url()).toMatch(/^https:\/\/frontend-production-6d80\.up\.railway\.app\//);
  });

  test('navigating to /dashboard after logout redirects back to /', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('demo_logged_out', 'true');
    });
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/$/);
  });

  test('authenticated visit to / redirects to /dashboard', async ({ page }) => {
    await page.goto('/');
    // Auto-login runs; we should end up at /dashboard
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test('Go to Main button has production Railway href', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('demo_logged_out', 'true');
    });
    await page.goto('/');
    const mainBtn = page.getByRole('button', { name: /Go to Main/i }).first();
    await expect(mainBtn).toBeVisible();
    // Without actually navigating, stub the handler by checking the onclick fires a redirect
    // We listen for a navigation request to the production URL
    const navigationPromise = page.waitForRequest(/frontend-production-6d80\.up\.railway\.app/, {
      timeout: 10_000,
    });
    await mainBtn.click().catch(() => {/* may navigate away */});
    const req = await navigationPromise.catch(() => null);
    expect(req, 'Expected navigation to the production Railway URL').not.toBeNull();
  });
});
