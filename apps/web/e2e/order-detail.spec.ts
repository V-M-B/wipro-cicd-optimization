import { expect, test } from './fixtures/mockApi';

test.describe('order detail', () => {
  test('shows customer, lines and totals', async ({ page, backend }) => {
    const order = backend.orders.find((o) => o.id === 'O-10003');
    await page.goto('/orders/O-10003');
    await expect(page.getByRole('heading', { level: 1, name: 'Order O-10003' })).toBeVisible();
    await expect(page.getByText('chen.wei@example.com')).toBeVisible();
    await expect(page.getByRole('table', { name: 'Order lines' }).locator('tbody tr')).toHaveCount(order?.lines.length ?? 0);
    await expect(page.getByTestId('order-total')).toHaveText(`$${order?.total.toFixed(2)}`);
  });

  test('walks an order through its whole lifecycle', async ({ page, backend }) => {
    await page.goto('/orders/O-10001');
    for (const [action, label] of [
      ['Mark as paid', 'paid'],
      ['Mark as shipped', 'shipped'],
      ['Mark as delivered', 'delivered'],
    ]) {
      await page.getByRole('button', { name: action }).click();
      await expect(page.getByText(`Order O-10001 is now ${label}.`)).toBeVisible();
    }
    await expect(page.getByText('No further actions are available for this order.')).toBeVisible();
    expect(backend.orders.find((o) => o.id === 'O-10001')?.status).toBe('DELIVERED');
    const patches = backend.requests.filter((r) => r.method === 'PATCH').map((r) => r.body);
    expect(patches).toEqual([{ status: 'PAID' }, { status: 'SHIPPED' }, { status: 'DELIVERED' }]);
  });

  test('cancelling requires confirmation', async ({ page, backend }) => {
    await page.goto('/orders/O-10002');
    await page.getByRole('button', { name: 'Cancel order' }).click();
    await expect(page.getByRole('button', { name: 'Confirm cancellation' })).toBeVisible();
    expect(backend.requests.some((r) => r.method === 'PATCH')).toBe(false);
    await page.getByRole('button', { name: 'Confirm cancellation' }).click();
    await expect(page.getByText('This order was cancelled.')).toBeVisible();
    await expect(page.locator('.page-header [data-status]')).toHaveAttribute('data-status', 'CANCELLED');
  });

  test('shows a server conflict and leaves the order unchanged', async ({ page, backend }) => {
    backend.fail('PATCH', /^\/api\/orders\/O-10001$/, 409, { message: 'Order was modified by another user.' });
    await page.goto('/orders/O-10001');
    await page.getByRole('button', { name: 'Mark as paid' }).click();
    await expect(page.getByRole('alert')).toHaveText('Order was modified by another user.');
    await expect(page.locator('.page-header [data-status]')).toHaveAttribute('data-status', 'CREATED');
  });

  test('unknown orders show a not-found message', async ({ page }) => {
    await page.goto('/orders/O-99999');
    await expect(page.getByRole('heading', { name: 'Order not found' })).toBeVisible();
    await page.getByRole('link', { name: 'Back to orders' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Orders' })).toBeVisible();
  });

  test('is reachable from the order list', async ({ page }) => {
    await page.goto('/orders');
    await page.getByRole('link', { name: 'O-10033' }).click();
    await expect(page).toHaveURL('/orders/O-10033');
    await expect(page.getByText(/Created 2024-03-18/)).toBeVisible();
  });
});
