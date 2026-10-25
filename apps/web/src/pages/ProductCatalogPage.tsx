import { useCallback, useMemo, useState } from 'react';
import { useApi } from '../api/context';
import { EmptyState, ErrorBanner, Loading } from '../components/Feedback';
import { HighlightedText } from '../components/HighlightedText';
import { CategoryValues } from '../generated/schemas';
import type { Category } from '../generated/schemas';
import { useAsync } from '../hooks/useAsync';
import { errorMessage } from '../lib/api';
import { formatCurrency, humanizeEnum, pluralize } from '../lib/format';
import { searchProducts, sortProducts } from '../lib/search';
import type { ProductSort } from '../lib/search';

export function ProductCatalogPage() {
  const api = useApi();
  const load = useCallback((signal: AbortSignal) => api.listProducts(signal), [api]);
  const { state, reload } = useAsync(load);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<Category | 'ALL'>('ALL');
  const [includeInactive, setIncludeInactive] = useState(false);
  const [sort, setSort] = useState<ProductSort>('relevance');

  const results = useMemo(() => {
    if (state.status !== 'success') return [];
    return sortProducts(searchProducts(state.data, query, { category, includeInactive }), sort);
  }, [state, query, category, includeInactive, sort]);

  if (state.status === 'loading') return <Loading label="Loading products…" />;
  if (state.status === 'error') return <ErrorBanner message={errorMessage(state.error)} onRetry={reload} />;

  return (
    <div className="page">
      <h1>Product catalog</h1>
      <form className="filters" role="search" aria-label="Product filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Search products
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Name or SKU" />
        </label>
        <label>
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value as Category | 'ALL')}>
            <option value="ALL">All categories</option>
            {CategoryValues.map((c) => (
              <option key={c} value={c}>
                {humanizeEnum(c)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sort by
          <select value={sort} onChange={(e) => setSort(e.target.value as ProductSort)}>
            <option value="relevance">Relevance</option>
            <option value="name">Name</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
          </select>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />
          Show inactive
        </label>
      </form>
      <p className="result-summary" aria-live="polite">
        {pluralize(results.length, 'product')}
      </p>
      {results.length === 0 ? (
        <EmptyState title="No products found." />
      ) : (
        <table className="data-table" aria-label="Products">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Name</th>
              <th>Category</th>
              <th className="num">Price</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {results.map((p) => (
              <tr key={p.id} data-testid="product-row" className={p.active ? undefined : 'inactive'}>
                <td>
                  <code>
                    <HighlightedText text={p.sku} query={query} />
                  </code>
                </td>
                <td>
                  <HighlightedText text={p.name} query={query} />
                </td>
                <td>{humanizeEnum(p.category)}</td>
                <td className="num">{formatCurrency(p.unitPrice)}</td>
                <td>{p.active ? 'Active' : 'Inactive'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
