import { expect, test } from './fixtures/mockApi';

test.describe('navigation', () => {
  test('dashboard shows KPI cards from the API', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Orders', exact: true })).toContainText('34');
    await expect(page.getByRole('region', { name: 'Revenue', exact: true })).toContainText('$');
    await expect(page.getByRole('list', { name: 'Orders per day' }).getByRole('listitem')).toHaveCount(7);
  });

  test('main navigation reaches every page', async ({ page }) => {
    await page.goto('/');
    const nav = page.getByRole('navigation', { name: 'Main' });
    for (const [link, heading] of [
      ['Orders', 'Orders'],
      ['New order', 'New order'],
      ['Products', 'Product catalog'],
      ['Customers', 'Customers'],
      ['Dashboard', 'Dashboard'],
    ]) {
      await nav.getByRole('link', { name: link, exact: true }).click();
      await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible();
      await expect(nav.getByRole('link', { name: link, exact: true })).toHaveClass(/active/);
    }
  });

  test('deep links are served by the SPA fallback', async ({ page }) => {
    await page.goto('/orders/O-10002');
    await expect(page.getByRole('heading', { level: 1, name: 'Order O-10002' })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('heading', { level: 1, name: 'Order O-10002' })).toBeVisible();
  });

  test('unknown routes show the not-found page', async ({ page }) => {
    await page.goto('/reports/quarterly');
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
    await page.getByRole('link', { name: 'Go to the dashboard' }).click();
    await expect(page).toHaveURL('/');
  });

  test('browser back and forward work across pages', async ({ page }) => {
    await page.goto('/products');
    await page.getByRole('link', { name: 'Customers', exact: true }).click();
    await expect(page).toHaveURL('/customers');
    await page.goBack();
    await expect(page.getByRole('heading', { level: 1, name: 'Product catalog' })).toBeVisible();
    await page.goForward();
    await expect(page.getByRole('heading', { level: 1, name: 'Customers' })).toBeVisible();
  });

  test('dashboard status links open the filtered order list', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Shipped' }).click();
    await expect(page).toHaveURL('/orders?status=SHIPPED');
    await expect(page.getByLabel('Status')).toHaveValue('SHIPPED');
  });
});
