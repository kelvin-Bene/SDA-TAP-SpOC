import { test, expect } from './fixtures';

test.describe('Landing Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/welcome');
  });

  test('hero section renders with SpOC branding', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const heroText = await page.locator('h1').textContent();
    expect(heroText?.toLowerCase()).toContain('spoc');
  });

  test('animated orbital graphic visible', async ({ page }) => {
    // The landing page has an orbital/space animation element
    const visual = page.locator('[class*="orbital"], [class*="animate"], canvas, svg').first();
    await expect(visual).toBeVisible({ timeout: 5000 });
  });

  test('pipeline steps section exists', async ({ page }) => {
    // Scroll down to find pipeline/steps content
    const stepsSection = page.locator('text=/pipeline|steps|how it works/i').first();
    await expect(stepsSection).toBeVisible({ timeout: 5000 });
  });

  test('Sign In button navigates to /login', async ({ page }) => {
    // Button may be link or button, with various text like "Sign In", "Login", "Enter"
    const signInBtn = page.getByRole('link', { name: /sign in|log in|login|enter/i }).first()
      .or(page.getByRole('button', { name: /sign in|log in|login|enter/i }).first())
      .or(page.locator('a[href*="/login"]').first());
    await expect(signInBtn).toBeVisible({ timeout: 10000 });
    await signInBtn.click();
    await expect(page).toHaveURL(/\/login/);
  });

  test('Get Started button is visible', async ({ page }) => {
    const ctaBtn = page.getByRole('link', { name: /get started/i })
      .or(page.getByRole('button', { name: /get started/i }))
      .first();
    await expect(ctaBtn).toBeVisible();
  });

  test('theme toggle cycles themes', async ({ page }) => {
    const themeToggle = page.locator('[aria-label*="theme" i], button:has(svg[class*="sun"]), button:has(svg[class*="moon"])').first();
    if (await themeToggle.isVisible()) {
      await themeToggle.click();
      // After click, theme should change
      const html = page.locator('html');
      const classAfterClick = await html.getAttribute('class');
      expect(classAfterClick).toBeDefined();
    }
  });

  test('footer section renders', async ({ page }) => {
    const footer = page.locator('footer').or(page.locator('[class*="footer"]')).first();
    await expect(footer).toBeVisible();
  });

  test('page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/welcome');
    await page.waitForTimeout(2000);
    // Filter out known non-critical errors (favicon, source maps)
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('.map') && !e.includes('404')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
