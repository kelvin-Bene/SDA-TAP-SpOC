import { test, expect } from '../fixtures/consoleWatcher';

test.describe('P2 Depth — Profile page', () => {
  test('profile page shows Demo User with email', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.getByRole('heading', { name: 'Profile', level: 1 })).toBeVisible();
    await expect(page.getByLabel('Display Name')).toHaveValue('Demo User');
    await expect(page.getByLabel('Email')).toHaveValue(/demo@uct-benchmark/i);
  });

  test('profile stats cards show counts', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.getByText(/Member Since/i)).toBeVisible();
    await expect(page.getByText(/Total Submissions/i)).toBeVisible();
    await expect(page.getByText(/Best Score/i)).toBeVisible();
  });

  test('organization field has default value', async ({ page }) => {
    await page.goto('/profile');
    const orgInput = page.getByLabel('Organization');
    const value = await orgInput.inputValue();
    expect(value.length).toBeGreaterThan(0);
  });

  test('Save Changes button is present and clickable', async ({ page }) => {
    await page.goto('/profile');
    const saveBtn = page.getByRole('button', { name: /Save Changes/i });
    await expect(saveBtn).toBeVisible();
    await expect(saveBtn).toBeEnabled();
  });
});
