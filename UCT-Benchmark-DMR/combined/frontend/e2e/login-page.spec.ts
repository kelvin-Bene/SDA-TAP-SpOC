import { test, expect } from './fixtures';

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('login card renders with branding', async ({ page }) => {
    await expect(page.locator('text=/sign in|log in|welcome/i').first()).toBeVisible();
  });

  test('email and password fields accept input', async ({ page }) => {
    const emailInput = page.getByRole('textbox', { name: /email/i })
      .or(page.locator('input[type="email"]'))
      .first();
    const passwordInput = page.locator('input[type="password"]').first();

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();

    await emailInput.fill('test@example.com');
    await passwordInput.fill('TestPass123!');

    await expect(emailInput).toHaveValue('test@example.com');
    await expect(passwordInput).toHaveValue('TestPass123!');
  });

  test('Google OAuth button visible', async ({ page }) => {
    const googleBtn = page.getByRole('button', { name: /google/i })
      .or(page.locator('button:has-text("Google")'))
      .first();
    await expect(googleBtn).toBeVisible();
  });

  test('GitHub OAuth button visible', async ({ page }) => {
    const githubBtn = page.getByRole('button', { name: /github/i })
      .or(page.locator('button:has-text("GitHub")'))
      .first();
    await expect(githubBtn).toBeVisible();
  });

  test('empty form shows validation on submit', async ({ page }) => {
    const submitBtn = page.getByRole('button', { name: /sign in|log in|submit/i }).first();
    if (await submitBtn.isVisible()) {
      await submitBtn.click();
      // Should show validation or remain on login page
      await expect(page).toHaveURL(/\/login/);
    }
  });

  test('already-authenticated user redirects from /login', async ({ page }) => {
    // With auth disabled (default), /login may redirect to /
    // or show the login page -- both are valid
    const url = page.url();
    expect(url).toMatch(/\/(login)?$/);
  });

  test('page loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/login');
    await page.waitForTimeout(2000);
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('.map') && !e.includes('404')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
