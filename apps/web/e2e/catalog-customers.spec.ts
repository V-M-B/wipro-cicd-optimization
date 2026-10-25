import { expect, test } from './fixtures/mockApi';

test.describe('product catalog', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/products');
    await expect(page.getByTestId('product-row')).toHaveCount(11);
  });

  test('searches by name and highlights the match', async ({ page }) => {
    await page.getByRole('searchbox', { name: 'Search products' }).fill('train');
    await expect(page.getByTestId('product-row')).toHaveCount(1);
    await expect(page.locator('mark')).toHaveText(['Train']);
  });

  test('filters by category and sorts by price', async ({ page }) => {
    await page.getByLabel('Category').selectOption('ELECTRONICS');
    await page.getByLabel('Sort by').selectOption('price-asc');
    await expect(page.locator('[data-testid=product-row] td:first-child')).toHaveText(['ELE-1001', 'ELE-1002', 'ELE-1003']);
  });

  test('can show inactive products', async ({ page }) => {
    await page.getByRole('checkbox', { name: 'Show inactive' }).check();
    await expect(page.getByTestId('product-row')).toHaveCount(12);
    await expect(page.getByText('12 products')).toBeVisible();
    await expect(page.locator('tr.inactive')).toContainText('Legacy Wired Mouse');
  });
});

test.describe('customers', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/customers');
    await expect(page.getByTestId('customer-row')).toHaveCount(8);
  });

  test('filters by tier and region', async ({ page }) => {
    await page.getByLabel('Tier').selectOption('SILVER');
    await expect(page.locator('[data-testid=customer-row] td:first-child')).toHaveText(['Divya Menon', 'Grace Kim']);
    await page.getByLabel('Region').selectOption('EAST');
    await expect(page.locator('[data-testid=customer-row] td:first-child')).toHaveText(['Grace Kim']);
  });

  test('searches by email', async ({ page }) => {
    await page.getByRole('searchbox', { name: 'Search customers' }).fill('farid.haddad@');
    await expect(page.getByTestId('customer-row')).toHaveCount(1);
    await expect(page.getByTestId('customer-row')).toContainText('Farid Haddad');
  });

  test("opens a customer's orders in the order list", async ({ page }) => {
    await page.getByRole('link', { name: 'Orders for Chen Wei' }).click();
    await expect(page).toHaveURL('/orders?q=C-0003');
    for (const row of await page.getByTestId('order-row').all()) await expect(row).toContainText('Chen Wei');
  });
});
