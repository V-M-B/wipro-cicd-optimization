import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusBadge } from './StatusBadge';

describe('StatusBadge', () => {
  it.each([
    ['CREATED', 'Created'],
    ['PAID', 'Paid'],
    ['SHIPPED', 'Shipped'],
    ['DELIVERED', 'Delivered'],
    ['CANCELLED', 'Cancelled'],
  ] as const)('renders %s as %s', (status, label) => {
    render(<StatusBadge status={status} />);
    const badge = screen.getByText(label);
    expect(badge).toHaveAttribute('data-status', status);
    expect(badge).toHaveClass('badge', `badge-${status.toLowerCase()}`);
  });
});
