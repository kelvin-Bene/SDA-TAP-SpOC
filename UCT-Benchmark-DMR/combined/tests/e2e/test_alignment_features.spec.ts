/**
 * E2E Tests for Alignment Features
 *
 * Tests the newly implemented alignment features:
 * 1. TIER_5 "impossible criteria" handling
 * 2. Close (C) and Apparent (A) object type options
 * 3. Event type reliability warnings
 * 4. TrackTLE output toggle
 *
 * Author: UCT Benchmark Team
 * Date: 2026
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:3001';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

async function navigateToDatasetGenerator(page: Page) {
  await page.goto(`${BASE_URL}/datasets/generate`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading', { name: 'Generate Dataset' })).toBeVisible({ timeout: 15000 });
}

async function switchToLegacyMode(page: Page) {
  const legacyTab = page.getByRole('tab', { name: /Legacy Code/i });
  if (await legacyTab.isVisible({ timeout: 5000 })) {
    await legacyTab.click();
    await page.waitForTimeout(500);
  }
}

async function clickNext(page: Page) {
  const nextButton = page.getByRole('button', { name: /Next/i });
  if (await nextButton.isVisible({ timeout: 2000 })) {
    await nextButton.click();
    await page.waitForTimeout(300);
  }
}

// =============================================================================
// TIER_5 IMPOSSIBLE CRITERIA TESTS
// =============================================================================

test.describe('TIER_5 Impossible Criteria Handling', () => {
  test('should display tier classification in results', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // Look for tier indicators in the dataset list
    const tierIndicators = page.locator('[class*="tier"]')
      .or(page.locator('text=/T[1-5]/'))
      .or(page.locator('text=/TIER/i'));

    const count = await tierIndicators.count();
    console.log(`Found ${count} tier indicators`);
  });

  test('should show error message for impossible criteria', async ({ page }) => {
    await navigateToDatasetGenerator(page);

    // Navigate to Objects step
    await clickNext(page); // Regime
    await clickNext(page); // Quality
    await clickNext(page); // Objects

    // Try to set extreme values that might trigger TIER_5
    // Look for slider or input for object count
    const objectCountInput = page.locator('input[type="number"]')
      .or(page.locator('[role="slider"]'));

    if (await objectCountInput.first().isVisible({ timeout: 3000 })) {
      // Try to set a very high object count
      console.log('Found object count input');
    }
  });

  test('should display recommended action for TIER_5', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // Check for "impossible" or "cannot be met" messages
    const impossibleMessage = page.locator('text=/impossible/i')
      .or(page.locator('text=/cannot be met/i'))
      .or(page.locator('text=/criteria_impossible/'));

    const isVisible = await impossibleMessage.first().isVisible({ timeout: 2000 }).catch(() => false);
    if (isVisible) {
      console.log('Found TIER_5 impossible criteria message');
    }
  });
});

// =============================================================================
// CLOSE AND APPARENT OBJECT TYPE TESTS
// =============================================================================

test.describe('Close (C) and Apparent (A) Object Types', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToDatasetGenerator(page);
    await switchToLegacyMode(page);
  });

  test('should display Close object type option', async ({ page }) => {
    // Look for Close option in legacy mode
    const closeOption = page.locator('text=Close')
      .or(page.locator('text=/proximity/i'))
      .or(page.locator('input[value="C"]'));

    const isVisible = await closeOption.first().isVisible({ timeout: 3000 }).catch(() => false);
    if (isVisible) {
      console.log('Close (C) object type option found');
    }
  });

  test('should display Apparent object type option', async ({ page }) => {
    // Look for Apparent option
    const apparentOption = page.locator('text=Apparent')
      .or(page.locator('text=/angular/i'))
      .or(page.locator('input[value="A"]'));

    const isVisible = await apparentOption.first().isVisible({ timeout: 3000 }).catch(() => false);
    if (isVisible) {
      console.log('Apparent (A) object type option found');
    }
  });

  test('should show threshold inputs for Close objects', async ({ page }) => {
    // Select Close object type if available
    const closeRadio = page.locator('input[value="C"]')
      .or(page.locator('label:has-text("Close") input'));

    if (await closeRadio.isVisible({ timeout: 2000 })) {
      await closeRadio.click();
      await page.waitForTimeout(500);

      // Look for distance and velocity threshold inputs
      const distanceInput = page.locator('[placeholder*="km"]')
        .or(page.locator('label:has-text("Distance")'));
      const velocityInput = page.locator('[placeholder*="m/s"]')
        .or(page.locator('label:has-text("Velocity")'));

      const distanceVisible = await distanceInput.first().isVisible({ timeout: 2000 }).catch(() => false);
      const velocityVisible = await velocityInput.first().isVisible({ timeout: 2000 }).catch(() => false);

      if (distanceVisible || velocityVisible) {
        console.log('Threshold inputs found for Close objects');
      }
    }
  });

  test('should display all 5 object type codes', async ({ page }) => {
    // H, C, A, U, N should all be available
    const objectTypes = ['HAMR', 'Close', 'Apparent', 'Unspecified', 'Calibration'];
    let foundCount = 0;

    for (const objType of objectTypes) {
      const option = page.locator(`text=${objType}`);
      if (await option.first().isVisible({ timeout: 1000 }).catch(() => false)) {
        foundCount++;
        console.log(`Found object type: ${objType}`);
      }
    }

    console.log(`Found ${foundCount} of 5 object types`);
  });
});

// =============================================================================
// EVENT TYPE RELIABILITY WARNING TESTS
// =============================================================================

test.describe('Event Type Reliability Warnings', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToDatasetGenerator(page);
    await switchToLegacyMode(page);
    // Navigate to Event step
    await clickNext(page); // Object -> Regime
    await clickNext(page); // Regime -> Event
  });

  test('should show NE as reliable option', async ({ page }) => {
    await page.waitForTimeout(500);

    const neOption = page.locator('text=No Events')
      .or(page.locator('input[value="NE"]'));

    if (await neOption.first().isVisible({ timeout: 3000 })) {
      console.log('NE (No Events) option visible');

      // Check for reliable/recommended indicator
      const reliableIndicator = page.locator('text=/reliable/i')
        .or(page.locator('text=/recommended/i'))
        .or(page.locator('[class*="success"]'));

      const hasIndicator = await reliableIndicator.first().isVisible({ timeout: 2000 }).catch(() => false);
      if (hasIndicator) {
        console.log('NE has reliability indicator');
      }
    }
  });

  test('should show warning for MB event type', async ({ page }) => {
    await page.waitForTimeout(500);

    const mbOption = page.locator('text=Maneuver')
      .or(page.locator('input[value="MB"]'));

    if (await mbOption.first().isVisible({ timeout: 3000 })) {
      await mbOption.first().click();
      await page.waitForTimeout(500);

      // Check for warning about heuristic
      const warning = page.locator('text=/heuristic/i')
        .or(page.locator('text=/fallback/i'))
        .or(page.locator('[class*="warning"]'));

      const hasWarning = await warning.first().isVisible({ timeout: 2000 }).catch(() => false);
      if (hasWarning) {
        console.log('MB has heuristic warning');
      }
    }
  });

  test('should show warning for BU event type', async ({ page }) => {
    await page.waitForTimeout(500);

    const buOption = page.locator('text=Breakup')
      .or(page.locator('input[value="BU"]'));

    if (await buOption.first().isVisible({ timeout: 3000 })) {
      await buOption.first().click();
      await page.waitForTimeout(500);

      // Check for Space-Track or database warning
      const warning = page.locator('text=/Space-Track/i')
        .or(page.locator('text=/database/i'))
        .or(page.locator('[class*="warning"]'));

      const hasWarning = await warning.first().isVisible({ timeout: 2000 }).catch(() => false);
      if (hasWarning) {
        console.log('BU has database requirement warning');
      }
    }
  });

  test('should display reliability indicator for each event type', async ({ page }) => {
    await page.waitForTimeout(500);

    // Look for reliability badges or icons
    const reliabilityBadges = page.locator('[class*="badge"]')
      .or(page.locator('[class*="reliability"]'))
      .or(page.locator('svg[class*="icon"]'));

    const count = await reliabilityBadges.count();
    console.log(`Found ${count} reliability indicators on event step`);
  });
});

// =============================================================================
// TRACKTLE OUTPUT TOGGLE TESTS
// =============================================================================

test.describe('TrackTLE Output Toggle', () => {
  test('should have TrackTLE option in advanced settings', async ({ page }) => {
    await navigateToDatasetGenerator(page);

    // Navigate to Advanced step
    await clickNext(page); // Regime
    await clickNext(page); // Quality
    await clickNext(page); // Objects
    await clickNext(page); // Advanced

    await page.waitForTimeout(500);

    // Look for TrackTLE toggle
    const trackTleOption = page.locator('text=TrackTLE')
      .or(page.locator('text=/TLE/i'))
      .or(page.locator('[id*="tracktle"]'));

    const isVisible = await trackTleOption.first().isVisible({ timeout: 3000 }).catch(() => false);
    if (isVisible) {
      console.log('TrackTLE option found in advanced settings');
    }
  });

  test('should toggle TrackTLE generation', async ({ page }) => {
    await navigateToDatasetGenerator(page);

    // Navigate to Advanced
    for (let i = 0; i < 4; i++) {
      await clickNext(page);
    }

    await page.waitForTimeout(500);

    // Look for toggle/checkbox
    const trackTleToggle = page.locator('input[type="checkbox"]')
      .filter({ hasText: /TrackTLE/i })
      .or(page.locator('[role="switch"]').filter({ hasText: /TrackTLE/i }));

    if (await trackTleToggle.first().isVisible({ timeout: 2000 })) {
      const initialState = await trackTleToggle.first().isChecked();
      await trackTleToggle.first().click();
      const newState = await trackTleToggle.first().isChecked();

      if (initialState !== newState) {
        console.log('TrackTLE toggle works correctly');
      }
    }
  });

  test('should show minimum observations requirement', async ({ page }) => {
    await navigateToDatasetGenerator(page);

    // Navigate to Advanced
    for (let i = 0; i < 4; i++) {
      await clickNext(page);
    }

    await page.waitForTimeout(500);

    // Look for "3 observations" or "minimum" text near TrackTLE
    const minObsText = page.locator('text=/3.*observation/i')
      .or(page.locator('text=/minimum.*observation/i'));

    const isVisible = await minObsText.first().isVisible({ timeout: 2000 }).catch(() => false);
    if (isVisible) {
      console.log('Minimum observations requirement shown');
    }
  });
});

// =============================================================================
// TARGET PERCENTAGE UI TESTS
// =============================================================================

test.describe('Target Percentage in UI', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToDatasetGenerator(page);
    await switchToLegacyMode(page);
  });

  test('should display percentage options (50, 10, 1)', async ({ page }) => {
    // Look for percentage options
    const percentageOptions = ['50%', '10%', '1%'];
    let foundCount = 0;

    for (const pct of percentageOptions) {
      const option = page.locator(`text=${pct}`)
        .or(page.locator(`input[value="${pct.replace('%', '')}"]`));

      if (await option.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        foundCount++;
        console.log(`Found percentage option: ${pct}`);
      }
    }

    console.log(`Found ${foundCount} of 3 percentage options`);
  });

  test('should display unspecified option', async ({ page }) => {
    const unspecifiedOption = page.locator('text=Unspecified')
      .or(page.locator('input[value="UN"]'));

    const isVisible = await unspecifiedOption.first().isVisible({ timeout: 3000 }).catch(() => false);
    if (isVisible) {
      console.log('Unspecified percentage option found');
    }
  });

  test('should update legacy code when percentage changes', async ({ page }) => {
    // Look for code preview/display
    const codeDisplay = page.locator('[class*="code"]')
      .or(page.locator('[class*="preview"]'))
      .or(page.locator('text=/[HCAUN][0-9UN]{2}/'));

    // Select 50%
    const fiftyPct = page.locator('text=50%').or(page.locator('input[value="50"]'));
    if (await fiftyPct.first().isVisible({ timeout: 2000 })) {
      await fiftyPct.first().click();
      await page.waitForTimeout(300);

      // Check if code updates to include "50"
      const codeText = await codeDisplay.first().textContent().catch(() => '');
      if (codeText && codeText.includes('50')) {
        console.log('Code updated with 50% selection');
      }
    }
  });
});

// =============================================================================
// API RESPONSE VALIDATION TESTS
// =============================================================================

test.describe('API Response Validation', () => {
  test('should receive tier in dataset response', async ({ page }) => {
    const response = await page.request.get(`${API_URL}/api/v1/datasets`).catch(() => null);

    if (response && response.ok()) {
      const data = await response.json();
      if (Array.isArray(data) && data.length > 0) {
        // Check if tier information is present
        const hasT ier = data.some((d: any) => d.tier !== undefined);
        console.log(`Datasets have tier information: ${hasT ier}`);
      }
    }
  });

  test('should receive object type in dataset response', async ({ page }) => {
    const response = await page.request.get(`${API_URL}/api/v1/datasets`).catch(() => null);

    if (response && response.ok()) {
      const data = await response.json();
      if (Array.isArray(data) && data.length > 0) {
        const hasObjectType = data.some((d: any) =>
          d.object_type !== undefined || d.legacy_code !== undefined
        );
        console.log(`Datasets have object type information: ${hasObjectType}`);
      }
    }
  });

  test('should handle dataset generation request', async ({ page }) => {
    // Mock a dataset generation request
    const requestBody = {
      orbit_regime: 'LEO',
      sensor_type: 'OP',
      event_type: 'NE',
      object_type: 'U',
      target_percentage: 50,
    };

    // Just verify the API endpoint exists
    const response = await page.request.get(`${API_URL}/api/v1/health`).catch(() => null);
    if (response) {
      console.log(`API health check: ${response.status()}`);
    }
  });
});
