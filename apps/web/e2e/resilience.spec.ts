import { expect, test } from './fixtures/mockApi';

test.describe('API failure handling', () => {
  test('transparently retries a transient 503', async ({ page, backend }) => {
    backend.fail('GET', /^\/api\/products$/, 503, { message: 'warming up' }, 1);
    await page.goto('/products');
    await expect(page.getByTestId('product-row')).toHaveCount(11);
    expect(backend.requests.filter((r) => r.path === '/api/products')).toHaveLength(2);
  });

  test('shows an error after retries are exhausted and recovers on Retry', async ({ page, backend }) => {
    backend.fail('GET', /^\/api\/orders$/, 503, { message: 'Orders service unavailable' }, 3);
    await page.goto('/orders');
    await expect(page.getByRole('alert')).toHaveText(/Orders service unavailable/);
    await page.getByRole('button', { name: 'Retry' }).click();
    await expect(page.getByTestId('order-row')).toHaveCount(10);
  });

  test('does not retry client errors', async ({ page, backend }) => {
    backend.fail('GET', /^\/api\/customers$/, 403, { message: 'You do not have access to customers.' }, 5);
    await page.goto('/customers');
    await expect(page.getByRole('alert')).toHaveText(/You do not have access to customers\./);
    expect(backend.requests.filter((r) => r.path === '/api/customers')).toHaveLength(1);
  });

  test('keeps the local estimate when the quote service is down', async ({ page, backend }) => {
    backend.fail('POST', /^\/api\/quotes$/, 500, { message: 'quote engine crashed' }, 10);
    await page.goto('/orders/new');
    await page.getByLabel('Customer').selectOption('C-0002');
    await page.getByLabel('Product for line 1').selectOption('ELE-1001');
    await expect(page.getByRole('heading', { name: 'Price quote estimate' })).toBeVisible();
    await expect(page.getByTestId('quote-total')).toHaveText('$33.48');
  });
});
