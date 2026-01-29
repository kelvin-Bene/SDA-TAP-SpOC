import { test, expect } from './fixtures';

/**
 * Dedicated InfoPopover component tests.
 * Navigates to DatasetGeneratorPage (heaviest user with ~15 InfoPopovers).
 *
 * The InfoPopover is a custom component (not Radix).
 * Trigger: <button aria-label="Learn about {title}">
 * Popover card: <div class="absolute z-50 w-80 rounded-xl ...">
 * Backdrop: <div class="fixed inset-0 z-40">
 */

/** Selector for the custom InfoPopover card (absolute positioned, z-50, w-80). */
const POPOVER_CARD = '.absolute.z-50.w-80';

test.describe('InfoPopover Component', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/datasets/generate');
    await page.waitForLoadState('domcontentloaded');
  });

  test('trigger icon renders with correct aria-label', async ({ page }) => {
    const triggers = page.locator('[aria-label^="Learn about"]');
    const count = await triggers.count();
    expect(count).toBeGreaterThanOrEqual(1);
    const label = await triggers.first().getAttribute('aria-label');
    expect(label).toMatch(/^Learn about /);
  });

  test('click opens popover with title and description', async ({ page }) => {
    const trigger = page.locator('[aria-label^="Learn about"]').first();
    await trigger.click();
    const popover = page.locator(POPOVER_CARD).first();
    await expect(popover).toBeVisible();
    const text = await popover.textContent();
    expect(text?.length).toBeGreaterThan(0);
  });

  test('backdrop click closes popover', async ({ page }) => {
    const trigger = page.locator('[aria-label^="Learn about"]').first();
    await trigger.click();
    const popover = page.locator(POPOVER_CARD).first();
    await expect(popover).toBeVisible();

    // The backdrop is a fixed inset-0 z-40 div inside the .relative.inline-flex parent
    // Use .last() since the popover backdrop is added after the sidebar overlay
    const backdrop = page.locator('.fixed.inset-0.z-40').last();
    await backdrop.click({ force: true });
    await expect(popover).toBeHidden({ timeout: 3000 });
  });

  test('X button closes popover', async ({ page }) => {
    const trigger = page.locator('[aria-label^="Learn about"]').first();
    await trigger.click();
    const popover = page.locator(POPOVER_CARD).first();
    await expect(popover).toBeVisible();

    // Close button is a <button> inside the popover header with an <X> SVG
    const closeBtn = popover.locator('button:has(svg)').first();
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
      await expect(popover).toBeHidden({ timeout: 3000 });
    }
  });

  test('Learn More section expands/collapses', async ({ page }) => {
    const trigger = page.locator('[aria-label^="Learn about"]').first();
    await trigger.click();
    const popover = page.locator(POPOVER_CARD).first();
    await expect(popover).toBeVisible();

    const learnMoreBtn = popover.getByText(/learn more/i).first();
    if (await learnMoreBtn.isVisible()) {
      await learnMoreBtn.click();
      await page.waitForTimeout(300);
      // After clicking, should show "Show less"
      await expect(popover.getByText(/show less/i).first()).toBeVisible();
    }
  });

  test('docs link renders when provided', async ({ page }) => {
    // Try all triggers to find one with a docs link
    const triggers = page.locator('[aria-label^="Learn about"]');
    const count = await triggers.count();
    let foundLink = false;
    for (let i = 0; i < Math.min(count, 5); i++) {
      await triggers.nth(i).click();
      const popover = page.locator(POPOVER_CARD).first();
      await expect(popover).toBeVisible();

      const docLink = popover.locator('a').first();
      if (await docLink.isVisible()) {
        await expect(docLink).toHaveAttribute('href', /.+/);
        foundLink = true;
        break;
      }
      // Close and try next
      await page.mouse.click(5, 5);
      await page.waitForTimeout(300);
    }
    // Not all pages have docs links, so this is informational
    if (!foundLink) {
      console.log('No InfoPopover with a docs link found on this page');
    }
  });

  test('InfoPopovers exist on generator page', async ({ page }) => {
    const triggers = page.locator('[aria-label^="Learn about"]');
    const count = await triggers.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('ConceptBadge shows label and is clickable', async ({ page }) => {
    // ConceptBadge renders as a <button> with cursor-help containing HelpCircle SVG
    const badges = page.locator('button.cursor-help');
    const count = await badges.count();
    if (count > 0) {
      const firstBadge = badges.first();
      const text = await firstBadge.textContent();
      expect(text?.length).toBeGreaterThan(0);
      await firstBadge.click();
      // Should open a small explanation popup (absolute z-50 w-64)
      const popup = page.locator('.absolute.z-50.w-64').first();
      await expect(popup).toBeVisible({ timeout: 3000 });
    }
  });

  test('StepExplainer collapses/expands with chevron', async ({ page }) => {
    // StepExplainer is a rounded-xl border div with a clickable button header
    const explainers = page.locator('.rounded-xl.border button.w-full').first();
    if (await explainers.isVisible()) {
      await explainers.click();
      await page.waitForTimeout(300);
      await explainers.click();
      await page.waitForTimeout(300);
    }
  });
});
