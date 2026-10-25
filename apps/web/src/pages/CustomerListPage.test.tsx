import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { formatCurrency } from '../lib/format';
import { customerStats } from '../lib/kpi';
import { orders } from '../test/fixtures';
import { renderWithProviders } from '../test/utils';
import { CustomerListPage } from './CustomerListPage';

async function renderCustomers() {
  const result = renderWithProviders(<CustomerListPage />);
  await screen.findByRole('table', { name: 'Customers' });
  return result;
}

const names = () => screen.getAllByTestId('customer-row').map((row) => (row as HTMLTableRowElement).cells[0]?.textContent);

describe('CustomerListPage', () => {
  it('lists customers alphabetically', async () => {
    await renderCustomers();
    expect(names()).toEqual([
      'Asha Rao',
      'Ben Carter',
      'Chen Wei',
      'Divya Menon',
      'Elena Garcia',
      'Farid Haddad',
      'Grace Kim',
      'Hiro Tanaka',
    ]);
  });

  it('shows order counts and lifetime value from the order history', async () => {
    await renderCustomers();
    const stats = customerStats(orders).get('C-0003');
    const row = screen.getAllByTestId('customer-row')[2] as HTMLTableRowElement;
    expect(within(row).getByRole('link', { name: 'Orders for Chen Wei' })).toHaveTextContent(String(stats?.orderCount));
    expect(row).toHaveTextContent(formatCurrency(stats?.lifetimeValue ?? 0));
  });

  it('links to the orders of a customer', async () => {
    await renderCustomers();
    expect(screen.getByRole('link', { name: 'Orders for Asha Rao' })).toHaveAttribute('href', '/orders?q=C-0001');
  });

  it('searches by name or email and highlights matches', async () => {
    const { user } = await renderCustomers();
    await user.type(screen.getByRole('searchbox', { name: 'Search customers' }), 'tanaka');
    expect(names()).toEqual(['Hiro Tanaka']);
    expect(screen.getByText('Tanaka', { selector: 'mark' })).toBeInTheDocument();
  });

  it.each([
    ['Tier', 'GOLD', ['Chen Wei', 'Farid Haddad']],
    ['Region', 'WEST', ['Divya Menon', 'Hiro Tanaka']],
  ])('filters by %s', async (label, value, expected) => {
    const { user } = await renderCustomers();
    await user.selectOptions(screen.getByLabelText(label), value);
    expect(names()).toEqual(expected);
  });

  it('shows an empty state when nothing matches', async () => {
    const { user } = await renderCustomers();
    await user.type(screen.getByRole('searchbox', { name: 'Search customers' }), 'zzz');
    expect(screen.getByText('No customers found.')).toBeInTheDocument();
  });
});
