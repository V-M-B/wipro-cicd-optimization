import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { FIXED_NOW, findOrder } from '../test/fixtures';
import { createMockApi, renderWithProviders } from '../test/utils';
import type { RenderOptions } from '../test/utils';
import { OrderDetailPage } from './OrderDetailPage';

async function renderOrder(id: string, options: RenderOptions = {}) {
  const result = renderWithProviders(<OrderDetailPage />, { route: `/orders/${id}`, path: '/orders/:orderId', ...options });
  await screen.findByRole('heading', { name: new RegExp(`Order ${id}|Order not found`) });
  return result;
}

const actions = () => within(screen.getByRole('region', { name: 'Order actions' }));

describe('OrderDetailPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(FIXED_NOW);
  });

  it('shows the order, its lines and its customer', async () => {
    await renderOrder('O-10002');
    const order = findOrder('O-10002');
    expect(screen.getByText('Ben Carter')).toBeInTheDocument();
    expect(screen.getByText('ben.carter@example.com')).toBeInTheDocument();
    const lines = screen.getByRole('table', { name: 'Order lines' });
    expect(within(lines).getAllByRole('row')).toHaveLength(1 + order.lines.length + 2 + (order.couponCode ? 1 : 0));
    expect(screen.getByTestId('order-total')).toHaveTextContent(`$${order.total.toFixed(2)}`);
  });

  it('shows when the order was created relative to now', async () => {
    await renderOrder('O-10034');
    expect(screen.getByText(/Created 2024-03-19 \d{2}:00 UTC \(\d+ hours? ago\)/)).toBeInTheDocument();
  });

  it.each([
    ['O-10001', ['Mark as paid', 'Cancel order']],
    ['O-10002', ['Mark as shipped', 'Cancel order']],
    ['O-10003', ['Mark as delivered']],
  ])('%s offers %j', async (id, labels) => {
    await renderOrder(id);
    expect(actions().getAllByRole('button').map((b) => b.textContent)).toEqual(labels);
  });

  it('offers no actions for terminal orders', async () => {
    await renderOrder('O-10004');
    expect(actions().queryAllByRole('button')).toHaveLength(0);
    expect(screen.getByText('No further actions are available for this order.')).toBeInTheDocument();
  });

  it('moves an order to the next status', async () => {
    const { user, api } = await renderOrder('O-10001');
    await user.click(screen.getByRole('button', { name: 'Mark as paid' }));
    expect(api.updateOrderStatus).toHaveBeenCalledWith('O-10001', 'PAID');
    expect(await screen.findByText('Order O-10001 is now paid.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mark as shipped' })).toBeInTheDocument();
  });

  it('asks for confirmation before cancelling', async () => {
    const { user, api } = await renderOrder('O-10002');
    await user.click(screen.getByRole('button', { name: 'Cancel order' }));
    expect(api.updateOrderStatus).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Keep order' }));
    expect(screen.queryByRole('button', { name: 'Confirm cancellation' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancel order' }));
    await user.click(screen.getByRole('button', { name: 'Confirm cancellation' }));
    expect(api.updateOrderStatus).toHaveBeenCalledWith('O-10002', 'CANCELLED');
    expect(await screen.findByText('This order was cancelled.')).toBeInTheDocument();
  });

  it('reports a failed transition and keeps the order unchanged', async () => {
    const api = createMockApi();
    api.updateOrderStatus.mockRejectedValue(new ApiError('conflict', 'The record was changed by someone else.', 409));
    const { user } = await renderOrder('O-10001', { api });
    await user.click(screen.getByRole('button', { name: 'Mark as paid' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The record was changed by someone else.');
    expect(screen.getByRole('button', { name: 'Mark as paid' })).toBeEnabled();
  });

  it('shows a not-found page for unknown orders', async () => {
    await renderOrder('O-99999');
    expect(screen.getByRole('link', { name: 'Back to orders' })).toHaveAttribute('href', '/orders');
  });

  it('still renders when the customer cannot be loaded', async () => {
    const api = createMockApi();
    api.getCustomer.mockRejectedValue(new ApiError('server', 'boom', 500));
    await renderOrder('O-10001', { api });
    expect(screen.getByText(/could not be loaded/)).toHaveTextContent('Customer C-0001 could not be loaded.');
  });
});
