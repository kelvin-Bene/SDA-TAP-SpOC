import { test, expect } from '../fixtures/consoleWatcher';

/**
 * P1 Core — Sample UCTP Files card on /submit (demo-only).
 * Card is gated behind VITE_DEMO_MODE; buttons disabled until a target dataset is selected.
 */
test.describe('P1 Core — Sample UCTP Files card', () => {
  test('card renders on /submit in demo mode', async ({ page }) => {
    await page.goto('/submit');
    await expect(page.getByRole('heading', { name: /Sample UCTP Files/i })).toBeVisible();
    await expect(page.getByText(/Don't have your own UCTP output/i)).toBeVisible();
  });

  test('all three quality-sample buttons present', async ({ page }) => {
    await page.goto('/submit');
    await expect(page.getByRole('button', { name: /High-Quality Sample/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Medium-Quality Sample/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Low-Quality Sample/i })).toBeVisible();
  });

  test('buttons disabled until a dataset is selected', async ({ page }) => {
    await page.goto('/submit');
    await expect(page.getByRole('button', { name: /High-Quality Sample/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /Medium-Quality Sample/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /Low-Quality Sample/i })).toBeDisabled();
    await expect(page.getByText(/Select a target dataset below first/i)).toBeVisible();
  });

  test('selecting a dataset enables the three sample buttons', async ({ page }) => {
    await page.goto('/submit');
    // Open Target Dataset combobox and pick the first option
    await page.getByRole('combobox').filter({ hasText: /Select a dataset/i }).click();
    await page.getByRole('option').first().click();
    await expect(page.getByRole('button', { name: /High-Quality Sample/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /Medium-Quality Sample/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /Low-Quality Sample/i })).toBeEnabled();
  });

  for (const quality of ['High', 'Medium', 'Low'] as const) {
    test(`${quality}-Quality Sample click triggers download with correct filename`, async ({ page }) => {
      await page.goto('/submit');
      await page.getByRole('combobox').filter({ hasText: /Select a dataset/i }).click();
      await page.getByRole('option').first().click();

      const [download] = await Promise.all([
        page.waitForEvent('download'),
        page.getByRole('button', { name: new RegExp(`${quality}-Quality Sample`, 'i') }).click(),
      ]);

      expect(download.suggestedFilename()).toMatch(
        new RegExp(`sample_uctp_dataset\\d+_${quality.toLowerCase()}\\.json$`),
      );
    });
  }

  test('downloaded sample has UCTP shape (sourcedData + epoch)', async ({ page }) => {
    await page.goto('/submit');
    await page.getByRole('combobox').filter({ hasText: /Select a dataset/i }).click();
    await page.getByRole('option').first().click();

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /Medium-Quality Sample/i }).click(),
    ]);

    const path = await download.path();
    expect(path).toBeTruthy();
    const fs = await import('fs');
    const content = fs.readFileSync(path!, 'utf8');
    const parsed = JSON.parse(content);
    expect(Array.isArray(parsed)).toBe(true);
    expect(parsed.length).toBeGreaterThan(0);
    expect(parsed[0]).toHaveProperty('sourcedData');
    expect(Array.isArray(parsed[0].sourcedData)).toBe(true);
    expect(parsed[0]).toHaveProperty('epoch');
  });
});
