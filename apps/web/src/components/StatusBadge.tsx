import type { OrderStatus } from '../generated/schemas';
import { STATUS_DESCRIPTIONS, STATUS_LABELS } from '../lib/orderStatus';

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`badge badge-${status.toLowerCase()}`} data-status={status} title={STATUS_DESCRIPTIONS[status]}>
      {STATUS_LABELS[status]}
    </span>
  );
}
