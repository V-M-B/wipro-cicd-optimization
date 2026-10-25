import { OrderStatusValues, RegionValues } from '../generated/schemas';
import type { OrderStatus, Region } from '../generated/schemas';
import { humanizeEnum } from '../lib/format';
import { STATUS_LABELS } from '../lib/orderStatus';
import { PAGE_SIZE_OPTIONS } from '../lib/queryState';
import type { OrderListState } from '../lib/queryState';

export interface OrderFiltersProps {
  state: OrderListState;
  onChange: (patch: Partial<OrderListState>) => void;
  onReset: () => void;
}

export function OrderFilters({ state, onChange, onReset }: OrderFiltersProps) {
  return (
    <form className="filters" role="search" aria-label="Order filters" onSubmit={(e) => e.preventDefault()}>
      <label>
        Status
        <select value={state.status} onChange={(e) => onChange({ status: e.target.value as OrderStatus | 'ALL' })}>
          <option value="ALL">All statuses</option>
          {OrderStatusValues.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Region
        <select value={state.region} onChange={(e) => onChange({ region: e.target.value as Region | 'ALL' })}>
          <option value="ALL">All regions</option>
          {RegionValues.map((r) => (
            <option key={r} value={r}>
              {humanizeEnum(r)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Search
        <input
          type="search"
          placeholder="Order id, customer or SKU"
          value={state.text}
          onChange={(e) => onChange({ text: e.target.value })}
        />
      </label>
      <label>
        Per page
        <select value={state.pageSize} onChange={(e) => onChange({ pageSize: Number(e.target.value) })}>
          {PAGE_SIZE_OPTIONS.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={onReset}>
        Reset filters
      </button>
    </form>
  );
}
