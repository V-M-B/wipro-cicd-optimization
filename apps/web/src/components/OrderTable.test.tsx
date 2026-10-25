import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { Order } from '../generated/schemas';
import { indexCustomers } from '../lib/orderQuery';
import type { SortSpec } from '../lib/orderQuery';
import { customers, findOrder } from '../test/fixtures';
import { OrderTable } from './OrderTable';

const sample: Order[] = [findOrder('O-10001'), findOrder('O-10002'), { ...findOrder('O-10003'), customerId: 'C-0404' }];

function setup(sort: SortSpec = { key: 'createdAt', direction: 'desc' }) {
  const onSort = vi.fn();
  render(
    <MemoryRouter>
      <OrderTable orders={sample} customers={indexCustomers(customers)} sort={sort} onSort={onSort} />
    </MemoryRouter>,
  );
  return { onSort, user: userEvent.setup() };
}

describe('OrderTable', () => {
  it('renders one row per order with a link to its detail page', () => {
    setup();
    const rows = screen.getAllByTestId('order-row');
    expect(rows).toHaveLength(3);
    expect(within(rows[0] as HTMLElement).getByRole('link', { name: 'O-10001' })).toHaveAttribute('href', '/orders/O-10001');
  });

  it('shows customer names, formatted dates and totals', () => {
    setup();
    const first = screen.getAllByTestId('order-row')[0] as HTMLElement;
    const order = findOrder('O-10001');
    expect(first).toHaveTextContent('Asha Rao');
    expect(first).toHaveTextContent('Mar 1, 2024');
    expect(first).toHaveTextContent(`$${order.total.toFixed(2)}`);
  });

  it('falls back to the customer id for unknown customers', () => {
    setup();
    expect(screen.getAllByTestId('order-row')[2]).toHaveTextContent('C-0404');
  });

  it('marks the active sort column', () => {
    setup({ key: 'total', direction: 'asc' });
    expect(screen.getByRole('columnheader', { name: /Total/ })).toHaveAttribute('aria-sort', 'ascending');
    expect(screen.getByRole('columnheader', { name: /Created/ })).toHaveAttribute('aria-sort', 'none');
  });

  it.each([
    ['Order', 'id'],
    ['Customer', 'customer'],
    ['Total', 'total'],
  ])('clicking %s requests sorting by %s', async (label, key) => {
    const { onSort, user } = setup();
    await user.click(screen.getByRole('button', { name: new RegExp(`^${label}`) }));
    expect(onSort).toHaveBeenCalledWith(key);
  });
});
