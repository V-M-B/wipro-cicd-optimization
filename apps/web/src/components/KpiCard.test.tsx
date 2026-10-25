import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { KpiCard } from './KpiCard';

describe('KpiCard', () => {
  it('exposes the label as the accessible name of the card', () => {
    render(<KpiCard label="Average order value" value="$42.00" />);
    const card = screen.getByRole('region', { name: 'Average order value' });
    expect(within(card).getByText('$42.00')).toHaveClass('kpi-value');
  });

  it('renders an optional hint', () => {
    const { rerender } = render(<KpiCard label="Revenue" value="$1.00" />);
    expect(screen.queryByText('Paid only')).not.toBeInTheDocument();
    rerender(<KpiCard label="Revenue" value="$1.00" hint="Paid only" />);
    expect(screen.getByText('Paid only')).toBeInTheDocument();
  });

  it.each(['neutral', 'good', 'warning'] as const)('applies the %s tone', (tone) => {
    render(<KpiCard label="Orders" value="3" tone={tone} />);
    expect(screen.getByRole('region', { name: 'Orders' })).toHaveClass(`kpi-${tone}`);
  });
});
