import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { products } from '../test/fixtures';
import { OrderLineEditor } from './OrderLineEditor';
import type { DraftLine, OrderLineEditorProps } from './OrderLineEditor';

const active = products.filter((p) => p.active);

function setup(line: DraftLine, props: Partial<OrderLineEditorProps> = {}) {
  const onChange = vi.fn();
  const onRemove = vi.fn();
  render(
    <OrderLineEditor
      index={0}
      line={line}
      products={active}
      canRemove
      onChange={onChange}
      onRemove={onRemove}
      {...props}
    />,
  );
  return { onChange, onRemove, user: userEvent.setup() };
}

describe('OrderLineEditor', () => {
  it('lists active products with prices', () => {
    setup({ key: 1, sku: '', quantity: '1' });
    const select = screen.getByLabelText('Product for line 1');
    expect(select.querySelectorAll('option')).toHaveLength(active.length + 1);
    expect(screen.getByRole('option', { name: 'ELE-1001 — Wireless Mouse ($24.99)' })).toBeInTheDocument();
  });

  it('emits product and quantity changes', async () => {
    const { onChange, user } = setup({ key: 1, sku: '', quantity: '1' });
    await user.selectOptions(screen.getByLabelText('Product for line 1'), 'GRO-2001');
    expect(onChange).toHaveBeenLastCalledWith({ key: 1, sku: 'GRO-2001', quantity: '1' });
    await user.type(screen.getByLabelText('Quantity for line 1'), '2');
    expect(onChange).toHaveBeenLastCalledWith({ key: 1, sku: '', quantity: '12' });
  });

  it('shows the line amount once a product and quantity are chosen', () => {
    setup({ key: 1, sku: 'ELE-1001', quantity: '3' });
    expect(screen.getByLabelText('Line 1 amount')).toHaveTextContent('$74.97');
  });

  it('shows validation errors and marks the fields invalid', () => {
    setup({ key: 7, sku: '', quantity: '0' }, { errors: { sku: 'Select a product', quantity: 'Quantity must be at least 1' } });
    expect(screen.getByLabelText('Product for line 1')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Quantity for line 1')).toHaveAccessibleDescription('Quantity must be at least 1');
    expect(screen.getByText('Select a product', { selector: '.field-error' })).toBeInTheDocument();
  });

  it('can only be removed when allowed', async () => {
    const { onRemove, user } = setup({ key: 1, sku: '', quantity: '1' }, { canRemove: false });
    const button = screen.getByRole('button', { name: 'Remove line 1' });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(onRemove).not.toHaveBeenCalled();
  });
});
