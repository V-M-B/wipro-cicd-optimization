import { useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api/context';
import { ErrorBanner, Loading } from '../components/Feedback';
import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';
import { OrderStatusValues, RegionValues } from '../generated/schemas';
import { useAsync } from '../hooks/useAsync';
import { errorMessage } from '../lib/api';
import { formatCurrency, formatNumber, formatPercent, humanizeEnum } from '../lib/format';
import { computeDashboard } from '../lib/kpi';

export function DashboardPage() {
  const api = useApi();
  const load = useCallback(
    (signal: AbortSignal) => Promise.all([api.listOrders({}, signal), api.listCustomers(signal)]),
    [api],
  );
  const { state, reload } = useAsync(load);

  const kpis = useMemo(
    () => (state.status === 'success' ? computeDashboard(state.data[0], state.data[1], new Date()) : null),
    [state],
  );

  if (state.status === 'loading') return <Loading label="Loading dashboard…" />;
  if (state.status === 'error' || !kpis) {
    return <ErrorBanner message={errorMessage(state.error)} onRetry={reload} />;
  }

  const maxDaily = Math.max(1, ...kpis.last7Days.map((d) => d.count));

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <div className="kpi-grid">
        <KpiCard label="Revenue" value={formatCurrency(kpis.revenue)} hint="Paid, shipped and delivered" />
        <KpiCard label="Orders" value={formatNumber(kpis.orderCount)} />
        <KpiCard label="Average order value" value={formatCurrency(kpis.averageOrderValue)} />
        <KpiCard
          label="Open orders"
          value={formatNumber(kpis.openOrders)}
          tone={kpis.openOrders > 0 ? 'warning' : 'neutral'}
        />
        <KpiCard label="Fulfillment rate" value={formatPercent(kpis.fulfillmentRate, 1)} tone="good" />
        <KpiCard label="Cancellation rate" value={formatPercent(kpis.cancellationRate, 1)} />
      </div>

      <div className="panels">
        <section aria-labelledby="by-status">
          <h2 id="by-status">Orders by status</h2>
          <ul className="plain-list">
            {OrderStatusValues.map((status) => (
              <li key={status}>
                <Link to={`/orders?status=${status}`}>
                  <StatusBadge status={status} />
                </Link>{' '}
                <span data-testid={`status-count-${status}`}>{kpis.byStatus[status]}</span>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="by-region">
          <h2 id="by-region">Revenue by region</h2>
          <table className="data-table compact" aria-label="Revenue by region">
            <tbody>
              {RegionValues.map((region) => (
                <tr key={region}>
                  <th scope="row">{humanizeEnum(region)}</th>
                  <td className="num">{formatCurrency(kpis.byRegion[region])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section aria-labelledby="top-skus">
          <h2 id="top-skus">Top products</h2>
          {kpis.topSkus.length === 0 ? (
            <p>No sales yet.</p>
          ) : (
            <ol className="plain-list" aria-label="Top products">
              {kpis.topSkus.map((item) => (
                <li key={item.sku}>
                  <code>{item.sku}</code> &middot; {formatNumber(item.quantity)} units ({formatPercent(item.share)})
                </li>
              ))}
            </ol>
          )}
        </section>

        <section aria-labelledby="last-7">
          <h2 id="last-7">Last 7 days</h2>
          <ul className="bars" aria-label="Orders per day">
            {kpis.last7Days.map((day) => (
              <li key={day.date} title={`${day.date}: ${day.count}`}>
                <span className="bar-label">{day.date.slice(5)}</span>
                <span className="bar" style={{ width: `${(day.count / maxDaily) * 100}%` }} />
                <span className="bar-value">{day.count}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
