import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api/context';
import { EmptyState, ErrorBanner, Loading } from '../components/Feedback';
import { HighlightedText } from '../components/HighlightedText';
import { CustomerTierValues, RegionValues } from '../generated/schemas';
import type { CustomerTier, Region } from '../generated/schemas';
import { useAsync } from '../hooks/useAsync';
import { errorMessage } from '../lib/api';
import { formatCurrency, humanizeEnum, pluralize } from '../lib/format';
import { customerStats } from '../lib/kpi';
import { matchesQuery } from '../lib/search';

export function CustomerListPage() {
  const api = useApi();
  const load = useCallback(
    (signal: AbortSignal) => Promise.all([api.listCustomers(signal), api.listOrders({}, signal)]),
    [api],
  );
  const { state, reload } = useAsync(load);
  const [query, setQuery] = useState('');
  const [tier, setTier] = useState<CustomerTier | 'ALL'>('ALL');
  const [region, setRegion] = useState<Region | 'ALL'>('ALL');

  const stats = useMemo(() => customerStats(state.status === 'success' ? state.data[1] : []), [state]);
  const rows = useMemo(() => {
    if (state.status !== 'success') return [];
    return state.data[0]
      .filter((c) => tier === 'ALL' || c.tier === tier)
      .filter((c) => region === 'ALL' || c.region === region)
      .filter((c) => matchesQuery(`${c.name} ${c.email} ${c.id}`, query))
      .sort((a, b) => a.name.localeCompare(b.name, 'en'));
  }, [state, query, tier, region]);

  if (state.status === 'loading') return <Loading label="Loading customers…" />;
  if (state.status === 'error') return <ErrorBanner message={errorMessage(state.error)} onRetry={reload} />;

  return (
    <div className="page">
      <h1>Customers</h1>
      <form className="filters" role="search" aria-label="Customer filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Search customers
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Name or email" />
        </label>
        <label>
          Tier
          <select value={tier} onChange={(e) => setTier(e.target.value as CustomerTier | 'ALL')}>
            <option value="ALL">All tiers</option>
            {CustomerTierValues.map((t) => (
              <option key={t} value={t}>
                {humanizeEnum(t)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Region
          <select value={region} onChange={(e) => setRegion(e.target.value as Region | 'ALL')}>
            <option value="ALL">All regions</option>
            {RegionValues.map((r) => (
              <option key={r} value={r}>
                {humanizeEnum(r)}
              </option>
            ))}
          </select>
        </label>
      </form>
      <p className="result-summary" aria-live="polite">
        {pluralize(rows.length, 'customer')}
      </p>
      {rows.length === 0 ? (
        <EmptyState title="No customers found." />
      ) : (
        <table className="data-table" aria-label="Customers">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Tier</th>
              <th>Region</th>
              <th className="num">Orders</th>
              <th className="num">Lifetime value</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => {
              const s = stats.get(c.id) ?? { orderCount: 0, lifetimeValue: 0 };
              return (
                <tr key={c.id} data-testid="customer-row">
                  <td>
                    <HighlightedText text={c.name} query={query} />
                  </td>
                  <td>
                    <HighlightedText text={c.email} query={query} />
                  </td>
                  <td>{humanizeEnum(c.tier)}</td>
                  <td>{humanizeEnum(c.region)}</td>
                  <td className="num">
                    {s.orderCount > 0 ? (
                      <Link to={`/orders?q=${encodeURIComponent(c.id)}`} aria-label={`Orders for ${c.name}`}>
                        {s.orderCount}
                      </Link>
                    ) : (
                      0
                    )}
                  </td>
                  <td className="num">{formatCurrency(s.lifetimeValue)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
