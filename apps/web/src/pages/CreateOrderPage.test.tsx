import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ApiError } from '../lib/api';
import { createMockApi, renderWithProviders } from '../test/utils';
import type { MockApi } from '../test/utils';
import { CreateOrderPage } from './CreateOrderPage';

async function renderForm(api: MockApi = createMockApi()) {
  const result = renderWithProviders(<CreateOrderPage />, {
    api,
    route: '/orders/new',
    path: '/orders/new',
    extraRoutes: [{ path: '/orders/:orderId', element: <p>detail page</p> }],
  });
  await screen.findByRole('form', { name: 'Create order' });
  return { ...result, api };
}

describe('CreateOrderPage', () => {
  it('asks for a customer before quoting', async () => {
    await renderForm();
    expect(screen.getByText('Select a customer to see a price quote.')).toBeInTheDocument();
  });

  it('only offers active products', async () => {
    await renderForm();
    expect(screen.queryByRole('option', { name: /Legacy Wired Mouse/ })).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Wireless Mouse/ })).toBeInTheDocument();
  });

  it('validates on submit without calling the API', async () => {
    const { user, api } = await renderForm();
    await user.click(screen.getByRole('button', { name: 'Place order' }));
    expect(screen.getByText('Select a customer', { selector: '.field-error' })).toBeInTheDocument();
    expect(screen.getByText('Select a product', { selector: '.field-error' })).toBeInTheDocument();
    expect(api.createOrder).not.toHaveBeenCalled();
  });

  it('shows a live estimate, then the server-confirmed quote', async () => {
    const { user, api } = await renderForm();
    await user.selectOptions(screen.getByLabelText('Customer'), 'C-0002');
    await user.selectOptions(screen.getByLabelText('Product for line 1'), 'ELE-1001');
    await user.clear(screen.getByLabelText('Quantity for line 1'));
    await user.type(screen.getByLabelText('Quantity for line 1'), '2');
    expect(await screen.findByRole('heading', { name: 'Price quote confirmed by server' })).toBeInTheDocument();
    expect(api.getQuote).toHaveBeenLastCalledWith(
      { customerId: 'C-0002', lines: [{ sku: 'ELE-1001', quantity: 2 }] },
      expect.any(AbortSignal),
    );
    expect(screen.getByTestId('quote-total')).toHaveTextContent('$59.97');
  });

  it('falls back to the local estimate when the quote service fails', async () => {
    const api = createMockApi();
    api.getQuote.mockRejectedValue(new ApiError('unavailable', 'down', 503));
    const { user } = await renderForm(api);
    await user.selectOptions(screen.getByLabelText('Customer'), 'C-0002');
    await user.selectOptions(screen.getByLabelText('Product for line 1'), 'ELE-1001');
    await waitFor(() => expect(api.getQuote).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: 'Price quote estimate' })).toBeInTheDocument();
    expect(screen.getByTestId('quote-total')).toHaveTextContent('$33.48');
  });

  it('explains coupon problems', async () => {
    const { user } = await renderForm();
    await user.selectOptions(screen.getByLabelText('Customer'), 'C-0002');
    await user.selectOptions(screen.getByLabelText('Product for line 1'), 'GRO-2002');
    await user.type(screen.getByLabelText('Coupon code'), 'save10');
    expect(await screen.findByText('SAVE10 requires a minimum of $50.00')).toBeInTheDocument();
  });

  it('adds and removes lines and flags duplicates', async () => {
    const { user } = await renderForm();
    await user.click(screen.getByRole('button', { name: 'Add line' }));
    expect(screen.getAllByTestId('order-line')).toHaveLength(2);
    await user.selectOptions(screen.getByLabelText('Product for line 1'), 'TOY-5001');
    await user.selectOptions(screen.getByLabelText('Product for line 2'), 'TOY-5001');
    await user.click(screen.getByRole('button', { name: 'Place order' }));
    expect(screen.getByText('Duplicate of line 1')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Remove line 2' }));
    expect(screen.getAllByTestId('order-line')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Remove line 1' })).toBeDisabled();
  });

  it('creates the order and navigates to it', async () => {
    const { user, api } = await renderForm();
    await user.selectOptions(screen.getByLabelText('Customer'), 'C-0001');
    await user.selectOptions(screen.getByLabelText('Product for line 1'), 'HOM-4002');
    await user.type(screen.getByLabelText('Coupon code'), ' flat5 ');
    await user.click(screen.getByRole('button', { name: 'Place order' }));
    expect(await screen.findByText('detail page')).toBeInTheDocument();
    expect(api.createOrder).toHaveBeenCalledWith({
      customerId: 'C-0001',
      lines: [{ sku: 'HOM-4002', quantity: 1 }],
      couponCode: 'FLAT5',
    });
    expect(screen.getByTestId('location')).toHaveTextContent('/orders/O-20001');
  });

  it('shows server validation errors', async () => {
    const api = createMockApi();
    api.createOrder.mockRejectedValue(
      new ApiError('validation', 'Order rejected.', 422, { 'lines[0].sku': 'Product is out of stock.' }),
    );
    const { user } = await renderForm(api);
    await user.selectOptions(screen.getByLabelText('Customer'), 'C-0001');
    await user.selectOptions(screen.getByLabelText('Product for line 1'), 'HOM-4002');
    await user.click(screen.getByRole('button', { name: 'Place order' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Order rejected. Product is out of stock.');
    expect(screen.getByRole('button', { name: 'Place order' })).toBeEnabled();
  });
});
