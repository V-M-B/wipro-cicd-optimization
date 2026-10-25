import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { formatCurrency } from '../lib/format';
import { averageOrderValue, countByStatus, totalRevenue } from '../lib/kpi';
import { FIXED_NOW, orders } from '../test/fixtures';
import { createMockApi, renderWithProviders } from '../test/utils';
import { DashboardPage } from './DashboardPage';

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(FIXED_NOW);
  });

  it('shows a loading state, then the KPI cards', async () => {
    renderWithProviders(<DashboardPage />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading dashboard');
    const revenue = await screen.findByRole('region', { name: 'Revenue' });
    expect(revenue).toHaveTextContent(formatCurrency(totalRevenue(orders)));
    expect(screen.getByRole('region', { name: 'Orders' })).toHaveTextContent(String(orders.length));
    expect(screen.getByRole('region', { name: 'Average order value' })).toHaveTextContent(
      formatCurrency(averageOrderValue(orders)),
    );
  });

  it('breaks orders down by status with links to the filtered list', async () => {
    renderWithProviders(<DashboardPage />);
    await screen.findByRole('heading', { name: 'Orders by status' });
    const counts = countByStatus(orders);
    expect(screen.getByTestId('status-count-CANCELLED')).toHaveTextContent(String(counts.CANCELLED));
    expect(screen.getByTestId('status-count-DELIVERED')).toHaveTextContent(String(counts.DELIVERED));
    expect(screen.getByRole('link', { name: 'Paid' })).toHaveAttribute('href', '/orders?status=PAID');
  });

  it('lists revenue for every region and the top products', async () => {
    renderWithProviders(<DashboardPage />);
    const regions = await screen.findByRole('table', { name: 'Revenue by region' });
    expect(within(regions).getAllByRole('row')).toHaveLength(4);
    const top = screen.getByRole('list', { name: 'Top products' });
    expect(within(top).getAllByRole('listitem').length).toBeGreaterThan(0);
    expect(within(top).getAllByRole('listitem').length).toBeLessThanOrEqual(5);
  });

  it('charts the last seven days relative to the current date', async () => {
    renderWithProviders(<DashboardPage />);
    const bars = await screen.findByRole('list', { name: 'Orders per day' });
    const items = within(bars).getAllByRole('listitem');
    expect(items).toHaveLength(7);
    expect(items.at(-1)).toHaveAttribute('title', expect.stringMatching(/^2024-03-19: \d+$/));
  });

  it('shows an error with a working retry', async () => {
    const api = createMockApi();
    api.listOrders.mockRejectedValueOnce(new ApiError('unavailable', 'The service is temporarily unavailable.', 503));
    const { user } = renderWithProviders(<DashboardPage />, { api });
    expect(await screen.findByRole('alert')).toHaveTextContent('The service is temporarily unavailable.');
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('region', { name: 'Revenue' })).toBeInTheDocument();
    expect(api.listOrders).toHaveBeenCalledTimes(2);
  });
});
