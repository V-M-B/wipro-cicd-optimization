import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_LIST_STATE } from '../lib/queryState';
import { OrderFilters } from './OrderFilters';

function setup(state = DEFAULT_LIST_STATE) {
  const onChange = vi.fn();
  const onReset = vi.fn();
  const user = userEvent.setup();
  render(<OrderFilters state={state} onChange={onChange} onReset={onReset} />);
  return { onChange, onReset, user };
}

describe('OrderFilters', () => {
  it('shows the current state', () => {
    setup({ ...DEFAULT_LIST_STATE, status: 'PAID', region: 'EAST', text: 'asha', pageSize: 25 });
    expect(screen.getByLabelText('Status')).toHaveValue('PAID');
    expect(screen.getByLabelText('Region')).toHaveValue('EAST');
    expect(screen.getByRole('searchbox', { name: 'Search' })).toHaveValue('asha');
    expect(screen.getByLabelText('Per page')).toHaveValue('25');
  });

  it.each([
    ['Status', 'SHIPPED', { status: 'SHIPPED' }],
    ['Region', 'WEST', { region: 'WEST' }],
    ['Per page', '50', { pageSize: 50 }],
  ])('changing %s emits a patch', async (label, value, patch) => {
    const { onChange, user } = setup();
    await user.selectOptions(screen.getByLabelText(label), value);
    expect(onChange).toHaveBeenCalledWith(patch);
  });

  it('emits text changes as the user types', async () => {
    const { onChange, user } = setup();
    await user.type(screen.getByRole('searchbox', { name: 'Search' }), 'b');
    expect(onChange).toHaveBeenCalledWith({ text: 'b' });
  });

  it('resets filters', async () => {
    const { onReset, user } = setup();
    await user.click(screen.getByRole('button', { name: 'Reset filters' }));
    expect(onReset).toHaveBeenCalledTimes(1);
  });
});
