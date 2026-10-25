import type { OrderStatus } from '../generated/schemas';
import { STATUS_LABELS } from '../lib/orderStatus';

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`badge badge-${status.toLowerCase()}`} data-status={status}>
      {STATUS_LABELS[status]}
    </span>
  );
}
