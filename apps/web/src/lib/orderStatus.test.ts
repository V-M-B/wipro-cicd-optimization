import { describe, expect, it } from 'vitest';
import { OrderStatusValues } from '../generated/schemas';
import type { Order } from '../generated/schemas';
import {
  ACTION_LABELS,
  InvalidTransitionError,
  STATUS_LABELS,
  allowedTransitions,
  isCancellable,
  isTerminal,
  lifecycleStep,
  pathBetween,
  transitionOrder,
} from './orderStatus';

const order: Order = {
  id: 'O-10001',
  customerId: 'C-0001',
  status: 'CREATED',
  lines: [{ sku: 'ELE-1001', quantity: 1, unitPrice: 24.99 }],
  createdAt: '2024-03-01T09:00:00Z',
  total: 26.99,
};

describe('order status state machine', () => {
  it.each([
    ['CREATED', ['PAID', 'CANCELLED']],
    ['PAID', ['SHIPPED', 'CANCELLED']],
    ['SHIPPED', ['DELIVERED']],
    ['DELIVERED', []],
    ['CANCELLED', []],
  ] as const)('%s can move to %j', (status, expected) => {
    expect(allowedTransitions(status)).toEqual(expected);
  });

  it.each([
    ['CREATED', false, true, 0],
    ['PAID', false, true, 1],
    ['SHIPPED', false, false, 2],
    ['DELIVERED', true, false, 3],
    ['CANCELLED', true, false, -1],
  ] as const)('%s terminal=%s cancellable=%s step=%d', (status, terminal, cancellable, step) => {
    expect(isTerminal(status)).toBe(terminal);
    expect(isCancellable(status)).toBe(cancellable);
    expect(lifecycleStep(status)).toBe(step);
  });

  it('returns a new order object and leaves the original untouched', () => {
    const paid = transitionOrder(order, 'PAID');
    expect(paid).not.toBe(order);
    expect(paid.status).toBe('PAID');
    expect(order.status).toBe('CREATED');
    expect(paid.lines).toBe(order.lines);
  });

  it('describes rejected transitions', () => {
    try {
      transitionOrder({ ...order, status: 'DELIVERED' }, 'CANCELLED');
      expect.unreachable();
    } catch (error) {
      expect(error).toBeInstanceOf(InvalidTransitionError);
      const e = error as InvalidTransitionError;
      expect(e.from).toBe('DELIVERED');
      expect(e.to).toBe('CANCELLED');
      expect(e.message).toBe('Cannot move an order from DELIVERED to CANCELLED');
    }
  });

  it.each([
    ['CREATED', 'DELIVERED', ['CREATED', 'PAID', 'SHIPPED', 'DELIVERED']],
    ['CREATED', 'CANCELLED', ['CREATED', 'CANCELLED']],
    ['PAID', 'DELIVERED', ['PAID', 'SHIPPED', 'DELIVERED']],
    ['SHIPPED', 'SHIPPED', ['SHIPPED']],
    ['SHIPPED', 'CANCELLED', null],
    ['DELIVERED', 'CREATED', null],
  ] as const)('pathBetween(%s, %s) = %j', (from, to, expected) => {
    expect(pathBetween(from, to)).toEqual(expected);
  });

  it('has labels for every status', () => {
    for (const status of OrderStatusValues) {
      expect(STATUS_LABELS[status]).toMatch(/^[A-Z][a-z]+$/);
      expect(ACTION_LABELS[status]).toBeTruthy();
    }
  });
});
