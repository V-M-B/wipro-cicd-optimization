import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { QuoteSummary } from './QuoteSummary';

const quote = { subtotal: 60, discount: 6, tax: 4.32, shipping: 7.99, total: 66.31 };

describe('QuoteSummary', () => {
  it('renders every line of the quote', () => {
    render(<QuoteSummary quote={quote} source="server" />);
    expect(screen.getByTestId('quote-subtotal')).toHaveTextContent('$60.00');
    expect(screen.getByTestId('quote-discount')).toHaveTextContent('-$6.00');
    expect(screen.getByTestId('quote-tax')).toHaveTextContent('$4.32');
    expect(screen.getByTestId('quote-shipping')).toHaveTextContent('$7.99');
    expect(screen.getByTestId('quote-total')).toHaveTextContent('$66.31');
  });

  it.each([
    ['server', 'confirmed by server'],
    ['estimate', 'estimate'],
  ] as const)('labels a %s quote', (source, label) => {
    render(<QuoteSummary quote={quote} source={source} />);
    expect(screen.getByRole('heading', { name: `Price quote ${label}` })).toBeInTheDocument();
  });

  it('tells the user how far they are from free shipping', () => {
    render(<QuoteSummary quote={quote} source="estimate" />);
    expect(screen.getByText('Add $46.00 more for free shipping.')).toBeInTheDocument();
  });

  it('hides the hint once shipping is free', () => {
    render(<QuoteSummary quote={{ ...quote, shipping: 0, total: 58.32 }} source="estimate" />);
    expect(screen.queryByText(/free shipping/)).not.toBeInTheDocument();
  });

  it('shows coupon problems', () => {
    render(<QuoteSummary quote={quote} source="estimate" couponMessage='Unknown coupon code "X"' />);
    expect(screen.getByRole('status')).toHaveTextContent('Unknown coupon code "X"');
  });
});
