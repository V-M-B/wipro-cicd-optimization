import type { Page } from '@playwright/test';
import { expect, test } from './fixtures/mockApi';

async function fillBasicOrder(page: Page, quantity = '2') {
  await page.goto('/orders/new');
  await page.getByLabel('Customer').selectOption('C-0002');
  await page.getByLabel('Product for line 1').selectOption('ELE-1001');
  await page.getByLabel('Quantity for line 1').fill(quantity);
}

test.describe('create order', () => {
  test('shows a live, server-confirmed quote', async ({ page }) => {
    await fillBasicOrder(page);
    await expect(page.getByRole('heading', { name: 'Price quote confirmed by server' })).toBeVisible();
    await expect(page.getByTestId('quote-total')).toHaveText('$59.97');
    await page.getByLabel('Quantity for line 1').fill('3');
    await expect(page.getByTestId('quote-subtotal')).toHaveText('$74.97');
    await expect(page.getByTestId('quote-total')).toHaveText('$86.46');
  });

  test('applies a coupon to the quote', async ({ page }) => {
    await fillBasicOrder(page, '3');
    await page.getByLabel('Coupon code').fill('save10');
    await expect(page.getByTestId('quote-discount')).toHaveText('-$7.50');
    await expect(page.getByTestId('quote-total')).toHaveText('$78.51');
  });

  test('explains why a coupon does not apply', async ({ page }) => {
    await fillBasicOrder(page, '1');
    await page.getByLabel('Coupon code').fill('BIG50');
    await expect(page.getByText('BIG50 requires a minimum of $300.00')).toBeVisible();
    await page.getByLabel('Coupon code').fill('NOPE1');
    await expect(page.getByText('Unknown coupon code "NOPE1"')).toBeVisible();
  });

  test('validates the form before submitting', async ({ page, backend }) => {
    await page.goto('/orders/new');
    await page.getByRole('button', { name: 'Place order' }).click();
    await expect(page.locator('.field-error')).toContainText(['Select a customer', 'Select a product']);
    await page.getByLabel('Quantity for line 1').fill('1000');
    await expect(page.getByText('Quantity must be at most 999')).toBeVisible();
    expect(backend.requests.some((r) => r.method === 'POST' && r.path === '/api/orders')).toBe(false);
  });

  test('creates a multi-line order and shows it in the list', async ({ page, backend }) => {
    await fillBasicOrder(page);
    await page.getByRole('button', { name: 'Add line' }).click();
    await page.getByLabel('Product for line 2').selectOption('HOM-4001');
    await page.getByLabel('Quantity for line 2').fill('4');
    await page.getByRole('button', { name: 'Place order' }).click();
    await expect(page).toHaveURL('/orders/O-20001');
    await expect(page.getByRole('status').filter({ hasText: 'Order created.' })).toBeVisible();
    await expect(page.getByRole('table', { name: 'Order lines' }).locator('tbody tr')).toHaveCount(2);
    const created = backend.requests.find((r) => r.method === 'POST' && r.path === '/api/orders');
    expect(created?.body).toEqual({
      customerId: 'C-0002',
      lines: [
        { sku: 'ELE-1001', quantity: 2 },
        { sku: 'HOM-4001', quantity: 4 },
      ],
    });
    await page.getByRole('link', { name: 'All orders' }).click();
    await expect(page.getByTestId('order-row').first()).toContainText('O-20001');
  });

  test('surfaces server-side validation errors', async ({ page, backend }) => {
    backend.fail('POST', /^\/api\/orders$/, 422, { message: 'Order rejected.', errors: { 'lines[0]': 'ELE-1001 is out of stock.' } });
    await fillBasicOrder(page);
    await page.getByRole('button', { name: 'Place order' }).click();
    await expect(page.getByRole('alert')).toHaveText('Order rejected. ELE-1001 is out of stock.');
    await expect(page).toHaveURL('/orders/new');
  });
});
