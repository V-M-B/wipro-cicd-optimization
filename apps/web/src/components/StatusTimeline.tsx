import type { OrderStatus } from '../generated/schemas';
import { LIFECYCLE, STATUS_LABELS, lifecycleStep } from '../lib/orderStatus';

export function StatusTimeline({ status }: { status: OrderStatus }) {
  const current = lifecycleStep(status);
  if (status === 'CANCELLED') {
    return (
      <p className="timeline-cancelled" data-testid="timeline">
        This order was cancelled.
      </p>
    );
  }
  return (
    <ol className="timeline" aria-label="Order progress" data-testid="timeline">
      {LIFECYCLE.map((step, i) => {
        const state = i < current ? 'done' : i === current ? 'current' : 'todo';
        return (
          <li key={step} className={`step step-${state}`} aria-current={state === 'current' ? 'step' : undefined}>
            {STATUS_LABELS[step]}
          </li>
        );
      })}
    </ol>
  );
}
