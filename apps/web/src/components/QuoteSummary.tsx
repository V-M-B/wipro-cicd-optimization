import type { PriceQuote } from '../generated/schemas';
import { amountToFreeShipping } from '../lib/cart';
import { formatCurrency } from '../lib/format';

export interface QuoteSummaryProps {
  quote: PriceQuote;
  source: 'server' | 'estimate';
  couponMessage?: string | undefined;
  pending?: boolean;
}

export function QuoteSummary({ quote, source, couponMessage, pending = false }: QuoteSummaryProps) {
  const remaining = amountToFreeShipping(quote.subtotal - quote.discount);
  const rows: Array<[string, number]> = [
    ['Subtotal', quote.subtotal],
    ['Discount', -quote.discount],
    ['Tax', quote.tax],
    ['Shipping', quote.shipping],
  ];
  return (
    <section className="quote" aria-labelledby="quote-title" aria-busy={pending}>
      <h2 id="quote-title">
        Price quote <small className="quote-source">{source === 'server' ? 'confirmed by server' : 'estimate'}</small>
      </h2>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label} className="quote-row">
            <dt>{label}</dt>
            <dd data-testid={`quote-${label.toLowerCase()}`}>{formatCurrency(value)}</dd>
          </div>
        ))}
        <div className="quote-row quote-total">
          <dt>Total</dt>
          <dd data-testid="quote-total">{formatCurrency(quote.total)}</dd>
        </div>
      </dl>
      {quote.subtotal > 0 && quote.shipping > 0 && remaining > 0 && (
        <p className="hint">Add {formatCurrency(remaining)} more for free shipping.</p>
      )}
      {couponMessage && (
        <p className="field-error" role="status">
          {couponMessage}
        </p>
      )}
    </section>
  );
}
