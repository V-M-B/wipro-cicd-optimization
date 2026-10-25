import { useCallback, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useApi } from '../api/context';
import { EmptyState, ErrorBanner, Loading } from '../components/Feedback';
import { OrderFilters } from '../components/OrderFilters';
import { OrderTable } from '../components/OrderTable';
import { Pagination } from '../components/Pagination';
import { useAsync } from '../hooks/useAsync';
import { errorMessage } from '../lib/api';
import { ordersToCsv } from '../lib/csv';
import { downloadText, exportFilename } from '../lib/download';
import { formatNumber, pluralize } from '../lib/format';
import { filterOrders, indexCustomers, nextSort, paginate, sortOrders } from '../lib/orderQuery';
import type { SortKey } from '../lib/orderQuery';
import { DEFAULT_LIST_STATE, parseOrderListState, serializeOrderListState, updateListState } from '../lib/queryState';
import type { OrderListState } from '../lib/queryState';

export function OrderListPage() {
  const api = useApi();
  const [searchParams, setSearchParams] = useSearchParams();
  const listState = useMemo(() => parseOrderListState(searchParams), [searchParams]);

  const load = useCallback(
    (signal: AbortSignal) => Promise.all([api.listOrders({}, signal), api.listCustomers(signal)]),
    [api],
  );
  const { state, reload } = useAsync(load);

  const customers = useMemo(
    () => indexCustomers(state.status === 'success' ? state.data[1] : []),
    [state],
  );
  const sorted = useMemo(() => {
    if (state.status !== 'success') return [];
    const filtered = filterOrders(
      state.data[0],
      { status: listState.status, region: listState.region, text: listState.text },
      customers,
    );
    return sortOrders(filtered, listState.sort, customers);
  }, [state, listState, customers]);

  const update = (patch: Partial<OrderListState>) =>
    setSearchParams(serializeOrderListState(updateListState(listState, patch)), { replace: true });

  const onSort = (key: SortKey) => update({ sort: nextSort(listState.sort, key) });

  const onExport = () => downloadText(exportFilename('orders', new Date()), ordersToCsv(sorted, customers));

  if (state.status === 'loading') return <Loading label="Loading orders…" />;
  if (state.status === 'error') return <ErrorBanner message={errorMessage(state.error)} onRetry={reload} />;

  const page = paginate(sorted, listState.page, listState.pageSize);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Orders</h1>
        <div className="actions">
          <button type="button" onClick={onExport} disabled={sorted.length === 0}>
            Export CSV
          </button>
          <Link className="button primary" to="/orders/new">
            New order
          </Link>
        </div>
      </div>
      <OrderFilters
        state={listState}
        onChange={update}
        onReset={() => setSearchParams(serializeOrderListState(DEFAULT_LIST_STATE), { replace: true })}
      />
      {page.totalItems === 0 ? (
        <EmptyState title="No orders match your filters." />
      ) : (
        <>
          <p className="result-summary" aria-live="polite">
            Showing {page.start}&ndash;{page.end} of {pluralize(page.totalItems, 'order')}
          </p>
          <OrderTable orders={page.items} customers={customers} sort={listState.sort} onSort={onSort} />
          <Pagination page={page.page} totalPages={page.totalPages} onChange={(p) => update({ page: p })} />
          <p className="muted">
            Page {formatNumber(page.page)} of {formatNumber(page.totalPages)}
          </p>
        </>
      )}
    </div>
  );
}
