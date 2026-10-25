import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusTimeline } from './StatusTimeline';

describe('StatusTimeline', () => {
  it.each([
    ['CREATED', 'Created', 0],
    ['PAID', 'Paid', 1],
    ['SHIPPED', 'Shipped', 2],
    ['DELIVERED', 'Delivered', 3],
  ] as const)('%s highlights the %s step', (status, label, done) => {
    render(<StatusTimeline status={status} />);
    const steps = screen.getAllByRole('listitem');
    expect(steps.map((s) => s.textContent)).toEqual(['Created', 'Paid', 'Shipped', 'Delivered']);
    expect(screen.getByText(label)).toHaveAttribute('aria-current', 'step');
    expect(steps.filter((s) => s.classList.contains('step-done'))).toHaveLength(done);
  });

  it('explains a cancelled order instead of showing progress', () => {
    render(<StatusTimeline status="CANCELLED" />);
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.getByTestId('timeline')).toHaveTextContent('This order was cancelled.');
  });
});
