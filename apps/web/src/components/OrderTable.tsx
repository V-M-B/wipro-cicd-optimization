import { Link } from 'react-router-dom';
import type { Order } from '../generated/schemas';
import { totalQuantity } from '../lib/cart';
import { formatCurrency, formatDate } from '../lib/format';
import type { CustomerIndex, SortKey, SortSpec } from '../lib/orderQuery';
import { StatusBadge } from './StatusBadge';

export interface OrderTableProps {
  orders: readonly Order[];
  customers: CustomerIndex;
  sort: SortSpec;
  onSort: (key: SortKey) => void;
}

const COLUMNS: Array<{ key: SortKey; label: string; numeric?: boolean }> = [
  { key: 'id', label: 'Order' },
  { key: 'createdAt', label: 'Created' },
  { key: 'customer', label: 'Customer' },
  { key: 'status', label: 'Status' },
  { key: 'total', label: 'Total', numeric: true },
];

export function OrderTable({ orders, customers, sort, onSort }: OrderTableProps) {
  return (
    <table className="data-table" aria-label="Orders">
      <thead>
        <tr>
          {COLUMNS.map((col) => {
            const active = sort.key === col.key;
            const ariaSort = active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none';
            return (
              <th key={col.key} aria-sort={ariaSort} className={col.numeric ? 'num' : undefined}>
                <button type="button" className="sort-button" onClick={() => onSort(col.key)}>
                  {col.label}
                  {active && <span aria-hidden="true">{sort.direction === 'asc' ? ' ▲' : ' ▼'}</span>}
                </button>
              </th>
            );
          })}
          <th className="num">Units</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((order) => (
          <tr key={order.id} data-testid="order-row">
            <td>
              <Link to={`/orders/${order.id}`}>{order.id}</Link>
            </td>
            <td>{formatDate(order.createdAt)}</td>
            <td>{customers.get(order.customerId)?.name ?? order.customerId}</td>
            <td>
              <StatusBadge status={order.status} />
            </td>
            <td className="num">{formatCurrency(order.total)}</td>
            <td className="num">{totalQuantity(order.lines)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
