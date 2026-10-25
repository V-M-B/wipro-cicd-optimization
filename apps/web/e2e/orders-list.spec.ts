import { readFile } from 'node:fs/promises';
import { expect, test } from './fixtures/mockApi';

const rows = (page: import('@playwright/test').Page) => page.getByTestId('order-row');

test.describe('order list', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orders');
    await expect(rows(page)).toHaveCount(10);
  });

  test('shows the newest orders first with a result summary', async ({ page }) => {
    await expect(rows(page).first()).toContainText('O-10034');
    await expect(page.getByText('Showing 1–10 of 34 orders')).toBeVisible();
  });

  test('filters by status and keeps the filter in the URL', async ({ page, backend }) => {
    await page.getByLabel('Status').selectOption('SHIPPED');
    await expect(page).toHaveURL(/status=SHIPPED/);
    const expected = backend.orders.filter((o) => o.status === 'SHIPPED').length;
    await expect(rows(page)).toHaveCount(expected);
    for (const badge of await page.locator('[data-status]').all()) {
      await expect(badge).toHaveAttribute('data-status', 'SHIPPED');
    }
  });

  test('filters by region and free text together', async ({ page }) => {
    await page.getByLabel('Region').selectOption('EAST');
    await page.getByRole('searchbox', { name: 'Search' }).fill('grace');
    await expect(rows(page).first()).toContainText('Grace Kim');
    for (const row of await rows(page).all()) await expect(row).toContainText('Grace Kim');
  });

  test('sorts by total when the header is clicked', async ({ page }) => {
    await page.getByRole('button', { name: /^Total/ }).click();
    await expect(page).toHaveURL(/sort=total&dir=desc/);
    const totals = (await page.locator('[data-testid=order-row] td:nth-child(5)').allTextContents()).map((t) =>
      Number(t.replace(/[$,]/g, '')),
    );
    expect(totals).toEqual([...totals].sort((a, b) => b - a));
  });

  test('paginates and changes page size', async ({ page }) => {
    await page.getByRole('button', { name: 'Next' }).click();
    await expect(page.getByText('Showing 11–20 of 34 orders')).toBeVisible();
    await page.getByLabel('Per page').selectOption('50');
    await expect(rows(page)).toHaveCount(34);
    await expect(page.getByRole('navigation', { name: 'Pagination' })).toHaveCount(0);
  });

  test('restores the view from the URL after a reload', async ({ page }) => {
    await page.getByLabel('Status').selectOption('DELIVERED');
    await page.getByRole('button', { name: /^Customer/ }).click();
    const before = await rows(page).allTextContents();
    await page.reload();
    await expect(page.getByLabel('Status')).toHaveValue('DELIVERED');
    expect(await rows(page).allTextContents()).toEqual(before);
  });

  test('exports the filtered list as a CSV download', async ({ page, backend }) => {
    await page.getByLabel('Status').selectOption('PAID');
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export CSV' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('orders-2024-03-19.csv');
    const csv = await readFile(await download.path(), 'utf8');
    const lines = csv.trim().split('\r\n');
    expect(lines[0]).toBe('Order ID,Created,Customer ID,Customer,Region,Status,Lines,Units,Coupon,Total');
    expect(lines).toHaveLength(backend.orders.filter((o) => o.status === 'PAID').length + 1);
  });
});
