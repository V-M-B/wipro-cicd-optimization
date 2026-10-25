import { screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { downloadText } from '../lib/download';
import { parseCsv } from '../lib/csv';
import { orders } from '../test/fixtures';
import { createMockApi, renderWithProviders } from '../test/utils';
import { OrderListPage } from './OrderListPage';

vi.mock('../lib/download', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/download')>();
  return { ...actual, downloadText: vi.fn() };
});

const rowIds = () =>
  screen.getAllByTestId('order-row').map((row) => within(row).getByRole('link').textContent);

async function renderList(route = '/orders') {
  const result = renderWithProviders(<OrderListPage />, { route, path: '/orders' });
  await screen.findByRole('table', { name: 'Orders' });
  return result;
}

describe('OrderListPage', () => {
  it('shows the newest orders first, ten per page', async () => {
    await renderList();
    expect(rowIds()).toEqual(['O-10034', 'O-10033', 'O-10032', 'O-10031', 'O-10030', 'O-10029', 'O-10028', 'O-10027', 'O-10026', 'O-10025']);
    expect(screen.getByText(/Showing 1–10 of 34 orders/)).toBeInTheDocument();
  });

  it('filters by status and records it in the URL', async () => {
    const { user } = await renderList();
    await user.selectOptions(screen.getByLabelText('Status'), 'CANCELLED');
    const cancelled = orders.filter((o) => o.status === 'CANCELLED').length;
    expect(screen.getAllByTestId('order-row')).toHaveLength(cancelled);
    expect(screen.getByTestId('location')).toHaveTextContent('/orders?status=CANCELLED');
  });

  it('filters by region through the customer', async () => {
    const { user } = await renderList();
    await user.selectOptions(screen.getByLabelText('Region'), 'EAST');
    for (const row of screen.getAllByTestId('order-row')) {
      expect(row).toHaveTextContent(/Chen Wei|Grace Kim/);
    }
  });

  it('searches by customer name', async () => {
    const { user } = await renderList();
    await user.type(screen.getByRole('searchbox', { name: 'Search' }), 'hiro');
    const rows = screen.getAllByTestId('order-row');
    expect(rows.length).toBeGreaterThan(0);
    rows.forEach((row) => expect(row).toHaveTextContent('Hiro Tanaka'));
  });

  it('restores filters, sort and page from the URL', async () => {
    await renderList('/orders?status=DELIVERED&sort=total&dir=asc');
    const totals = screen
      .getAllByTestId('order-row')
      .map((row) => Number((row.children[4]?.textContent ?? '').replace(/[$,]/g, '')));
    expect(totals).toEqual([...totals].sort((a, b) => a - b));
    expect(screen.getByLabelText('Status')).toHaveValue('DELIVERED');
    expect(screen.getByRole('columnheader', { name: /Total/ })).toHaveAttribute('aria-sort', 'ascending');
  });

  it('sorts when a column header is clicked', async () => {
    const { user } = await renderList();
    await user.click(screen.getByRole('button', { name: /^Order/ }));
    expect(rowIds()[0]).toBe('O-10001');
    expect(screen.getByTestId('location')).toHaveTextContent('sort=id&dir=asc');
  });

  it('paginates', async () => {
    const { user } = await renderList();
    await user.click(screen.getByRole('button', { name: 'Page 4' }));
    expect(rowIds()).toEqual(['O-10004', 'O-10003', 'O-10002', 'O-10001']);
    expect(screen.getByText(/Showing 31–34 of 34 orders/)).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('page=4');
  });

  it('shows an empty state and can reset filters', async () => {
    const { user } = renderWithProviders(<OrderListPage />, { route: '/orders?q=nobody', path: '/orders' });
    expect(await screen.findByText('No orders match your filters.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Reset filters' }));
    expect(await screen.findAllByTestId('order-row')).toHaveLength(10);
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/orders$/);
  });

  it('exports the filtered orders as CSV', async () => {
    const { user } = await renderList('/orders?status=PAID');
    await user.click(screen.getByRole('button', { name: 'Export CSV' }));
    expect(downloadText).toHaveBeenCalledTimes(1);
    const [filename, csv] = vi.mocked(downloadText).mock.calls[0] as [string, string];
    expect(filename).toMatch(/^orders-\d{4}-\d{2}-\d{2}\.csv$/);
    const rows = parseCsv(csv);
    expect(rows).toHaveLength(orders.filter((o) => o.status === 'PAID').length + 1);
    expect(rows.slice(1).every((r) => r[5] === 'PAID')).toBe(true);
  });

  it('shows an error when orders cannot be loaded', async () => {
    const api = createMockApi();
    api.listOrders.mockRejectedValue(new Error('Database offline'));
    renderWithProviders(<OrderListPage />, { api, route: '/orders', path: '/orders' });
    expect(await screen.findByRole('alert')).toHaveTextContent('Database offline');
  });
});
