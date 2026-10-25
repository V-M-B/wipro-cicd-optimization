import { useCallback, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { useApi } from '../api/context';
import { ErrorBanner, Loading } from '../components/Feedback';
import { StatusBadge } from '../components/StatusBadge';
import { StatusTimeline } from '../components/StatusTimeline';
import type { Customer, Order, OrderStatus } from '../generated/schemas';
import { useAsync } from '../hooks/useAsync';
import { ApiError, errorMessage } from '../lib/api';
import { cartSubtotal, lineTotal, totalQuantity } from '../lib/cart';
import { formatCurrency, formatDateTime, formatRelative, humanizeEnum } from '../lib/format';
import { ACTION_LABELS, STATUS_LABELS, allowedTransitions } from '../lib/orderStatus';

interface DetailData {
  order: Order;
  customer: Customer | null;
}

export function OrderDetailPage() {
  const api = useApi();
  const { orderId = '' } = useParams();
  const location = useLocation();
  const justCreated = (location.state as { created?: boolean } | null)?.created === true;

  const load = useCallback(
    async (signal: AbortSignal): Promise<DetailData> => {
      const order = await api.getOrder(orderId, signal);
      const customer = await api.getCustomer(order.customerId, signal).catch(() => null);
      return { order, customer };
    },
    [api, orderId],
  );
  const { state, reload, setData } = useAsync(load);
  const [pending, setPending] = useState<OrderStatus | null>(null);
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(justCreated ? 'Order created.' : null);

  if (state.status === 'loading') return <Loading label="Loading order…" />;
  if (state.status === 'error') {
    if (state.error instanceof ApiError && state.error.kind === 'not_found') {
      return (
        <div className="page">
          <h1>Order not found</h1>
          <p>
            No order with id <code>{orderId}</code> exists. <Link to="/orders">Back to orders</Link>
          </p>
        </div>
      );
    }
    return <ErrorBanner message={errorMessage(state.error)} onRetry={reload} />;
  }

  const { order, customer } = state.data;
  const transitions = allowedTransitions(order.status);

  const runTransition = async (to: OrderStatus) => {
    setActionError(null);
    setNotice(null);
    setPending(to);
    try {
      const updated = await api.updateOrderStatus(order.id, to);
      setData({ order: updated, customer });
      setNotice(`Order ${updated.id} is now ${STATUS_LABELS[updated.status].toLowerCase()}.`);
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setPending(null);
      setConfirmingCancel(false);
    }
  };

  const onAction = (to: OrderStatus) => {
    if (to === 'CANCELLED' && !confirmingCancel) {
      setConfirmingCancel(true);
      return;
    }
    void runTransition(to);
  };

  return (
    <div className="page">
      <p>
        <Link to="/orders">&larr; All orders</Link>
      </p>
      <div className="page-header">
        <h1>Order {order.id}</h1>
        <StatusBadge status={order.status} />
      </div>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {actionError && <ErrorBanner message={actionError} />}
      <p className="muted">
        Created {formatDateTime(order.createdAt)} ({formatRelative(order.createdAt, new Date())})
      </p>

      <StatusTimeline status={order.status} />

      <section className="actions" aria-label="Order actions">
        {transitions.length === 0 && <p className="muted">No further actions are available for this order.</p>}
        {transitions.map((to) => (
          <button
            key={to}
            type="button"
            className={to === 'CANCELLED' ? 'danger' : 'primary'}
            disabled={pending !== null}
            onClick={() => onAction(to)}
          >
            {to === 'CANCELLED' && confirmingCancel ? 'Confirm cancellation' : ACTION_LABELS[to]}
          </button>
        ))}
        {confirmingCancel && (
          <button type="button" onClick={() => setConfirmingCancel(false)} disabled={pending !== null}>
            Keep order
          </button>
        )}
        {pending && <span role="status">Updating&hellip;</span>}
      </section>

      <div className="panels">
        <section aria-labelledby="customer-title">
          <h2 id="customer-title">Customer</h2>
          {customer ? (
            <dl className="details">
              <dt>Name</dt>
              <dd>{customer.name}</dd>
              <dt>Email</dt>
              <dd>{customer.email}</dd>
              <dt>Tier</dt>
              <dd>{humanizeEnum(customer.tier)}</dd>
              <dt>Region</dt>
              <dd>{humanizeEnum(customer.region)}</dd>
            </dl>
          ) : (
            <p>
              Customer <code>{order.customerId}</code> could not be loaded.
            </p>
          )}
        </section>

        <section aria-labelledby="lines-title">
          <h2 id="lines-title">Lines</h2>
          <table className="data-table" aria-label="Order lines">
            <thead>
              <tr>
                <th>SKU</th>
                <th className="num">Quantity</th>
                <th className="num">Unit price</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {order.lines.map((line) => (
                <tr key={line.sku}>
                  <td>
                    <code>{line.sku}</code>
                  </td>
                  <td className="num">{line.quantity}</td>
                  <td className="num">{formatCurrency(line.unitPrice)}</td>
                  <td className="num">{formatCurrency(lineTotal(line))}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">Merchandise</th>
                <td className="num">{totalQuantity(order.lines)}</td>
                <td />
                <td className="num">{formatCurrency(cartSubtotal(order.lines))}</td>
              </tr>
              {order.couponCode && (
                <tr>
                  <th scope="row">Coupon</th>
                  <td colSpan={3} className="num">
                    {order.couponCode}
                  </td>
                </tr>
              )}
              <tr className="grand-total">
                <th scope="row">Order total</th>
                <td colSpan={3} className="num" data-testid="order-total">
                  {formatCurrency(order.total)}
                </td>
              </tr>
            </tfoot>
          </table>
        </section>
      </div>
    </div>
  );
}
