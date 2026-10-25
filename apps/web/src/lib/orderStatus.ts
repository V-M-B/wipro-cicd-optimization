import type { Order, OrderStatus } from '../generated/schemas';

/** Allowed status transitions. DELIVERED and CANCELLED are terminal. */
export const TRANSITIONS: Readonly<Record<OrderStatus, readonly OrderStatus[]>> = {
  CREATED: ['PAID', 'CANCELLED'],
  PAID: ['SHIPPED', 'CANCELLED'],
  SHIPPED: ['DELIVERED'],
  DELIVERED: [],
  CANCELLED: [],
};

/** The happy-path lifecycle in order. */
export const LIFECYCLE: readonly OrderStatus[] = ['CREATED', 'PAID', 'SHIPPED', 'DELIVERED'];

export const STATUS_LABELS: Readonly<Record<OrderStatus, string>> = {
  CREATED: 'Created',
  PAID: 'Paid',
  SHIPPED: 'Shipped',
  DELIVERED: 'Delivered',
  CANCELLED: 'Cancelled',
};

/** Button label for moving an order *into* the given status. */
export const ACTION_LABELS: Readonly<Record<OrderStatus, string>> = {
  CREATED: 'Reopen',
  PAID: 'Mark as paid',
  SHIPPED: 'Mark as shipped',
  DELIVERED: 'Mark as delivered',
  CANCELLED: 'Cancel order',
};

export class InvalidTransitionError extends Error {
  readonly from: OrderStatus;
  readonly to: OrderStatus;

  constructor(from: OrderStatus, to: OrderStatus) {
    super(`Cannot move an order from ${from} to ${to}`);
    this.name = 'InvalidTransitionError';
    this.from = from;
    this.to = to;
  }
}

export function canTransition(from: OrderStatus, to: OrderStatus): boolean {
  return TRANSITIONS[from].includes(to);
}

export function allowedTransitions(from: OrderStatus): readonly OrderStatus[] {
  return TRANSITIONS[from];
}

export function isTerminal(status: OrderStatus): boolean {
  return TRANSITIONS[status].length === 0;
}

export function isCancellable(status: OrderStatus): boolean {
  return canTransition(status, 'CANCELLED');
}

/** Return a copy of the order in the new status, or throw InvalidTransitionError. */
export function transitionOrder(order: Order, to: OrderStatus): Order {
  if (!canTransition(order.status, to)) {
    throw new InvalidTransitionError(order.status, to);
  }
  return { ...order, status: to };
}

/** Index in the happy-path lifecycle (0-3), or -1 for CANCELLED. */
export function lifecycleStep(status: OrderStatus): number {
  return LIFECYCLE.indexOf(status);
}

/** Shortest list of statuses from `from` to `to`, inclusive of both; null if unreachable. */
export function pathBetween(from: OrderStatus, to: OrderStatus): OrderStatus[] | null {
  const queue: OrderStatus[][] = [[from]];
  const visited = new Set<OrderStatus>([from]);
  while (queue.length > 0) {
    const path = queue.shift() as OrderStatus[];
    const last = path[path.length - 1] as OrderStatus;
    if (last === to) return path;
    for (const next of TRANSITIONS[last]) {
      if (!visited.has(next)) {
        visited.add(next);
        queue.push([...path, next]);
      }
    }
  }
  return null;
}
