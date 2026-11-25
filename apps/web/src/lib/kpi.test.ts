import { describe, expect, it } from 'vitest';
import type { Customer, Order } from '../generated/schemas';
import {
  averageOrderValue,
  cancellationRate,
  computeDashboard,
  countByStatus,
  customerStats,
  fulfillmentRate,
  ordersPerDay,
  revenueByRegion,
  topSkus,
  totalRevenue,
} from './kpi';
import { indexCustomers } from './orderQuery';

const customers: Customer[] = [
  { id: 'C-0001', name: 'A', email: 'a@example.com', tier: 'GOLD', region: 'NORTH' },
  { id: 'C-0002', name: 'B', email: 'b@example.com', tier: 'STANDARD', region: 'EAST' },
];

const order = (id: string, customerId: string, status: Order['status'], total: number, createdAt: string, lines: Array<[string, number]>): Order => ({
  id,
  customerId,
  status,
  total,
  createdAt,
  lines: lines.map(([sku, quantity]) => ({ sku, quantity, unitPrice: 1 })),
});

const orders: Order[] = [
  order('O-10001', 'C-0001', 'CREATED', 10, '2024-03-01T09:00:00Z', [['ELE-1001', 1]]),
  order('O-10002', 'C-0001', 'PAID', 20.1, '2024-03-02T09:00:00Z', [['ELE-1001', 2], ['GRO-2001', 5]]),
  order('O-10003', 'C-0002', 'SHIPPED', 30.2, '2024-03-02T18:00:00Z', [['GRO-2001', 1]]),
  order('O-10004', 'C-0002', 'DELIVERED', 40.3, '2024-03-04T09:00:00Z', [['TOY-5001', 3]]),
  order('O-10005', 'C-0001', 'CANCELLED', 99, '2024-03-05T09:00:00Z', [['HOM-4001', 50]]),
  order('O-10006', 'C-0009', 'DELIVERED', 5, '2024-03-05T10:00:00Z', [['APP-3001', 3]]),
];

describe('revenue KPIs', () => {
  it('counts paid, shipped and delivered orders only', () => {
    expect(totalRevenue(orders)).toBe(95.6);
  });

  it('averages over revenue orders', () => {
    expect(averageOrderValue(orders)).toBe(23.9);
  });

  it.each([
    [[], 0],
    [[orders[0] as Order], 0],
  ])('average is 0 without revenue orders (%#)', (list, expected) => {
    expect(averageOrderValue(list)).toBe(expected);
  });

  it('splits revenue by customer region, ignoring unknown customers', () => {
    expect(revenueByRegion(orders, indexCustomers(customers))).toEqual({ NORTH: 20.1, SOUTH: 0, EAST: 70.5, WEST: 0 });
  });
});

describe('status KPIs', () => {
  it('counts every status including zeros', () => {
    expect(countByStatus(orders)).toEqual({ CREATED: 1, PAID: 1, SHIPPED: 1, DELIVERED: 2, CANCELLED: 1 });
    expect(countByStatus([])).toEqual({ CREATED: 0, PAID: 0, SHIPPED: 0, DELIVERED: 0, CANCELLED: 0 });
  });

  it.each([
    ['fulfillment', fulfillmentRate, 2 / 5],
    ['cancellation', cancellationRate, 1 / 6],
  ] as const)('%s rate', (_name, fn, expected) => {
    expect(fn(orders)).toBeCloseTo(expected, 10);
    expect(fn([])).toBe(0);
  });
});

describe('volume KPIs', () => {
  it('ranks SKUs by units, excluding cancelled orders', () => {
    expect(topSkus(orders)).toEqual([
      { sku: 'GRO-2001', quantity: 6, share: 0.4 },
      { sku: 'APP-3001', quantity: 3, share: 0.2 },
      { sku: 'ELE-1001', quantity: 3, share: 0.2 },
      { sku: 'TOY-5001', quantity: 3, share: 0.2 },
    ]);
    expect(topSkus(orders, 1)).toEqual([{ sku: 'GRO-2001', quantity: 6, share: 0.4 }]);
  });

  it('reports a zero share when nothing has sold', () => {
    const cancelled = orders.map((o) => ({ ...o, status: 'CANCELLED' as const }));
    expect(topSkus(cancelled)).toEqual([]);
    expect(topSkus([])).toEqual([]);
  });

  it('buckets orders per UTC day over a trailing window', () => {
    expect(ordersPerDay(orders, new Date('2024-03-05T23:00:00Z'), 5)).toEqual([
      { date: '2024-03-01', count: 1 },
      { date: '2024-03-02', count: 2 },
      { date: '2024-03-03', count: 0 },
      { date: '2024-03-04', count: 1 },
      { date: '2024-03-05', count: 2 },
    ]);
  });

  it('computes per-customer order counts and lifetime value', () => {
    const stats = customerStats(orders);
    expect(stats.get('C-0001')).toEqual({ orderCount: 3, lifetimeValue: 20.1 });
    expect(stats.get('C-0002')).toEqual({ orderCount: 2, lifetimeValue: 70.5 });
    expect(stats.get('C-0404')).toBeUndefined();
  });
});

describe('computeDashboard', () => {
  it('assembles all KPIs', () => {
    const kpis = computeDashboard(orders, customers, new Date('2024-03-05T12:00:00Z'));
    expect(kpis).toMatchObject({
      revenue: 95.6,
      orderCount: 6,
      averageOrderValue: 23.9,
      openOrders: 3,
    });
    expect(kpis.last7Days).toHaveLength(7);
    expect(kpis.last7Days.at(-1)).toEqual({ date: '2024-03-05', count: 2 });
  });
});
