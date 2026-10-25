import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/context';
import { ErrorBanner, Loading } from '../components/Feedback';
import { OrderLineEditor } from '../components/OrderLineEditor';
import type { DraftLine } from '../components/OrderLineEditor';
import { QuoteSummary } from '../components/QuoteSummary';
import type { OrderLine, PriceQuote } from '../generated/schemas';
import { useAsync } from '../hooks/useAsync';
import { ApiError, errorMessage } from '../lib/api';
import type { QuoteRequest } from '../lib/api';
import { computeQuote, normalizeCouponCode } from '../lib/cart';
import { humanizeEnum } from '../lib/format';
import { MAX_ORDER_LINES, hasErrors, validateOrderDraft, validateQuantity } from '../lib/validators';

let nextLineKey = 1;
const newLine = (): DraftLine => ({ key: nextLineKey++, sku: '', quantity: '1' });

export function CreateOrderPage() {
  const api = useApi();
  const navigate = useNavigate();
  const load = useCallback(
    (signal: AbortSignal) => Promise.all([api.listCustomers(signal), api.listProducts(signal)]),
    [api],
  );
  const { state, reload } = useAsync(load);

  const [customerId, setCustomerId] = useState('');
  const [lines, setLines] = useState<DraftLine[]>(() => [newLine()]);
  const [couponCode, setCouponCode] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [serverQuote, setServerQuote] = useState<{ key: string; quote: PriceQuote } | null>(null);

  const customers = useMemo(() => (state.status === 'success' ? state.data[0] : []), [state]);
  const products = useMemo(
    () => (state.status === 'success' ? state.data[1].filter((p) => p.active) : []),
    [state],
  );
  const customer = customers.find((c) => c.id === customerId);
  const knownSkus = useMemo(() => new Set(products.map((p) => p.sku)), [products]);

  const pricedLines: OrderLine[] = useMemo(
    () =>
      lines.flatMap((line) => {
        const product = products.find((p) => p.sku === line.sku);
        if (!product || validateQuantity(line.quantity) !== null) return [];
        return [{ sku: product.sku, quantity: Number(line.quantity), unitPrice: product.unitPrice }];
      }),
    [lines, products],
  );

  const coupon = normalizeCouponCode(couponCode);
  const estimate = customer
    ? computeQuote({ lines: pricedLines, tier: customer.tier, region: customer.region, couponCode: coupon })
    : null;

  // Ask the server for an authoritative quote whenever the priced draft changes.
  const quoteKey =
    customer && pricedLines.length > 0 && pricedLines.length === lines.length
      ? JSON.stringify({
          customerId: customer.id,
          lines: pricedLines.map((l) => ({ sku: l.sku, quantity: l.quantity })),
          ...(coupon ? { couponCode: coupon } : {}),
        })
      : null;

  useEffect(() => {
    if (quoteKey === null) return undefined;
    const controller = new AbortController();
    const request = JSON.parse(quoteKey) as QuoteRequest;
    api.getQuote(request, controller.signal).then(
      (quote) => setServerQuote({ key: quoteKey, quote }),
      () => {
        // Keep showing the local estimate when the quote service is unavailable.
      },
    );
    return () => controller.abort();
  }, [api, quoteKey]);

  const errors = validateOrderDraft(
    { customerId, lines: lines.map((l) => ({ sku: l.sku, quantity: l.quantity })), couponCode: coupon },
    knownSkus,
  );
  const visibleErrors = submitted ? errors : { lines: {} };

  const updateLine = (index: number, line: DraftLine) =>
    setLines((current) => current.map((l, i) => (i === index ? line : l)));
  const removeLine = (index: number) => setLines((current) => current.filter((_, i) => i !== index));

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    setSubmitError(null);
    if (hasErrors(errors)) return;
    setSubmitting(true);
    try {
      const created = await api.createOrder({
        customerId,
        lines: lines.map((l) => ({ sku: l.sku, quantity: Number(l.quantity) })),
        ...(coupon ? { couponCode: coupon } : {}),
      });
      navigate(`/orders/${created.id}`, { state: { created: true } });
    } catch (error) {
      const details = error instanceof ApiError && error.details ? Object.values(error.details).join(' ') : '';
      setSubmitError(details ? `${errorMessage(error)} ${details}` : errorMessage(error));
      setSubmitting(false);
    }
  };

  if (state.status === 'loading') return <Loading label="Loading catalog…" />;
  if (state.status === 'error') return <ErrorBanner message={errorMessage(state.error)} onRetry={reload} />;

  const quoteToShow = serverQuote && serverQuote.key === quoteKey ? serverQuote.quote : estimate;

  return (
    <div className="page">
      <h1>New order</h1>
      <div className="panels">
        <form className="order-form" aria-label="Create order" noValidate onSubmit={onSubmit}>
          <label>
            Customer
            <select
              value={customerId}
              aria-invalid={visibleErrors.customerId ? true : undefined}
              onChange={(e) => setCustomerId(e.target.value)}
            >
              <option value="">Select a customer</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({humanizeEnum(c.tier)}, {humanizeEnum(c.region)})
                </option>
              ))}
            </select>
          </label>
          {visibleErrors.customerId && <span className="field-error">{visibleErrors.customerId}</span>}

          {lines.map((line, index) => (
            <OrderLineEditor
              key={line.key}
              index={index}
              line={line}
              products={products}
              errors={visibleErrors.lines[index]}
              canRemove={lines.length > 1}
              onChange={(l) => updateLine(index, l)}
              onRemove={() => removeLine(index)}
            />
          ))}
          <button
            type="button"
            onClick={() => setLines((current) => [...current, newLine()])}
            disabled={lines.length >= MAX_ORDER_LINES}
          >
            Add line
          </button>
          {visibleErrors.form && <p className="field-error">{visibleErrors.form}</p>}

          <label>
            Coupon code
            <input
              type="text"
              value={couponCode}
              autoComplete="off"
              aria-invalid={visibleErrors.couponCode ? true : undefined}
              onChange={(e) => setCouponCode(e.target.value)}
            />
          </label>
          {visibleErrors.couponCode && <span className="field-error">{visibleErrors.couponCode}</span>}

          {submitError && <ErrorBanner message={submitError} />}
          <button type="submit" className="primary" disabled={submitting}>
            {submitting ? 'Placing order…' : 'Place order'}
          </button>
        </form>

        <aside>
          {quoteToShow ? (
            <QuoteSummary
              quote={quoteToShow}
              source={quoteToShow === estimate ? 'estimate' : 'server'}
              couponMessage={estimate?.couponError}
              pending={quoteKey !== null && serverQuote?.key !== quoteKey}
            />
          ) : (
            <p className="muted">Select a customer to see a price quote.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
