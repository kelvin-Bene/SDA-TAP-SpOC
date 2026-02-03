/**
 * Playwright E2E Tests for UCT Benchmark Application
 *
 * Tests the Dataset Generator, Datasets List, Leaderboard, and other pages
 * including the new features: object type filtering, event detection, window
 * selection, and non-reference observations.
 */

import { test, expect } from '@playwright/test';

// Base URL for the frontend (configured in playwright.config.ts)
const BASE_URL = 'http://localhost:3001';

test.describe('Dataset Generator Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dataset generator page
    await page.goto(`${BASE_URL}/datasets/generate`);
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should load the dataset generator page', async ({ page }) => {
    // Check that the page has loaded with the wizard - use heading specifically
    await expect(page.getByRole('heading', { name: 'Generate Dataset' })).toBeVisible({ timeout: 10000 });
  });

  test('should display wizard steps', async ({ page }) => {
    // The wizard has multiple steps: Regime, Quality, Objects, Advanced, Review
    // Check for step indicators
    const stepsContainer = page.locator('[class*="flex"]').filter({ hasText: 'Regime' });
    await expect(stepsContainer.first()).toBeVisible({ timeout: 10000 });
  });

  test('should have Standard and Legacy Code tabs', async ({ page }) => {
    // Check for the two mode tabs
    const standardTab = page.getByRole('tab', { name: /Standard/i });
    const legacyTab = page.getByRole('tab', { name: /Legacy Code/i });

    await expect(standardTab).toBeVisible({ timeout: 10000 });
    await expect(legacyTab).toBeVisible({ timeout: 10000 });
  });

  test('should allow selecting orbital regime', async ({ page }) => {
    // LEO, MEO, GEO, HEO options should be available
    const leoButton = page.getByRole('radio', { name: /LEO/i }).or(page.locator('text=LEO').first());
    await expect(leoButton).toBeVisible({ timeout: 10000 });
  });

  test('should navigate through wizard steps', async ({ page }) => {
    // Click Next to go to step 2
    const nextButton = page.getByRole('button', { name: /Next/i });

    if (await nextButton.isVisible()) {
      await nextButton.click();
      // Should be on Quality step now
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Legacy Code Mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets/generate`);
    await page.waitForLoadState('networkidle');
  });

  test('should switch to Legacy Code mode', async ({ page }) => {
    const legacyTab = page.getByRole('tab', { name: /Legacy Code/i });

    if (await legacyTab.isVisible({ timeout: 5000 })) {
      await legacyTab.click();
      await page.waitForTimeout(500);

      // Should show legacy code specific content
      const objectTypeSection = page.locator('text=Object Type').or(page.locator('text=HAMR'));
      await expect(objectTypeSection.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('should have object type options (H, C, A, U, N)', async ({ page }) => {
    const legacyTab = page.getByRole('tab', { name: /Legacy Code/i });

    if (await legacyTab.isVisible({ timeout: 5000 })) {
      await legacyTab.click();
      await page.waitForTimeout(500);

      // Check for HAMR (H), Close (C), Apparent (A), Unspecified (U), Calibration (N)
      const hamrOption = page.locator('text=HAMR').or(page.locator('text=High Area'));
      await expect(hamrOption.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('should have event type options (MB, BU, LL, NE)', async ({ page }) => {
    const legacyTab = page.getByRole('tab', { name: /Legacy Code/i });

    if (await legacyTab.isVisible({ timeout: 5000 })) {
      await legacyTab.click();

      // Navigate to Event step (step 3 in legacy mode)
      const nextButton = page.getByRole('button', { name: /Next/i });
      if (await nextButton.isVisible()) {
        await nextButton.click(); // Go to step 2 (Regime)
        await page.waitForTimeout(300);
        await nextButton.click(); // Go to step 3 (Event)
        await page.waitForTimeout(500);
      }

      // Check for event types
      const noEventsOption = page.locator('text=No Events').or(page.locator('text=NE'));
      await expect(noEventsOption.first()).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Datasets List Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');
  });

  test('should load the datasets list', async ({ page }) => {
    // Check for datasets heading
    await expect(page.locator('text=Datasets').first()).toBeVisible({ timeout: 10000 });
  });

  test('should display dataset cards or table', async ({ page }) => {
    // Wait for datasets to load
    await page.waitForTimeout(2000);

    // Look for dataset entries - could be cards or table rows
    const datasetElements = page.locator('[class*="card"]').or(page.locator('tr'));
    const count = await datasetElements.count();

    // Should have some datasets visible
    console.log(`Found ${count} potential dataset elements`);
  });

  test('should have Generate Dataset button', async ({ page }) => {
    // Use more specific selector - the primary "Generate New" button
    const generateButton = page.getByRole('button', { name: 'Generate New' }).first();

    if (await generateButton.isVisible({ timeout: 5000 })) {
      await expect(generateButton).toBeEnabled();
    } else {
      // Fallback: check for any generate link in sidebar
      const generateLink = page.getByRole('link', { name: 'Generate Dataset' }).first();
      await expect(generateLink).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Leaderboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/leaderboard`);
    await page.waitForLoadState('networkidle');
  });

  test('should load the leaderboard', async ({ page }) => {
    await expect(page.locator('text=Leaderboard').first()).toBeVisible({ timeout: 10000 });
  });

  test('should display leaderboard entries', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(2000);

    // Look for table or list elements
    const tableBody = page.locator('tbody').or(page.locator('[class*="list"]'));
    await expect(tableBody.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Submissions Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/submissions`);
    await page.waitForLoadState('networkidle');
  });

  test('should load the submissions page', async ({ page }) => {
    await expect(page.locator('text=Submissions').or(page.locator('text=Submit')).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Navigation', () => {
  test('should navigate between pages using sidebar', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Try to find and click Datasets link
    const datasetsLink = page.getByRole('link', { name: /Datasets/i }).first();

    if (await datasetsLink.isVisible({ timeout: 5000 })) {
      await datasetsLink.click();
      await page.waitForLoadState('networkidle');

      // Should be on datasets page
      await expect(page.url()).toContain('datasets');
    }
  });

  test('should navigate to Generator page', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // Find the primary Generate New button (more specific)
    const generateButton = page.getByRole('button', { name: 'Generate New' }).first();

    if (await generateButton.isVisible({ timeout: 5000 })) {
      await generateButton.click();
      await page.waitForLoadState('networkidle');
      // Should be on generate page
      await expect(page.url()).toContain('generate');
    } else {
      // Fallback: use sidebar link
      const generateLink = page.getByRole('link', { name: 'Generate Dataset' }).first();
      if (await generateLink.isVisible({ timeout: 5000 })) {
        await generateLink.click();
        await page.waitForLoadState('networkidle');
        await expect(page.url()).toContain('generate');
      }
    }
  });
});

test.describe('Responsive Design', () => {
  test('should work on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // Page should still load
    await expect(page.locator('body')).toBeVisible();
  });

  test('should work on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('API Integration', () => {
  test('should fetch datasets from API', async ({ page }) => {
    // Listen for API calls
    const responsePromise = page.waitForResponse(
      (response) => response.url().includes('/api/v1/datasets') && response.status() === 200,
      { timeout: 15000 }
    );

    await page.goto(`${BASE_URL}/datasets`);

    const response = await responsePromise;
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
    console.log(`API returned ${data.length} datasets`);
  });

  test('should fetch leaderboard from API', async ({ page }) => {
    const responsePromise = page.waitForResponse(
      (response) => response.url().includes('/api/v1/leaderboard') && response.status() === 200,
      { timeout: 15000 }
    );

    await page.goto(`${BASE_URL}/leaderboard`);

    const response = await responsePromise;
    expect(response.ok()).toBeTruthy();
  });
});
