import { describe, expect, it } from 'vitest';
import type { Customer, Order } from '../generated/schemas';
import { filterOrders, indexCustomers, nextSort, sortOrders } from './orderQuery';
import type { OrderFilters, SortSpec } from './orderQuery';

const customers: Customer[] = [
  { id: 'C-0001', name: 'Zoë Adams', email: 'zoe@example.com', tier: 'GOLD', region: 'NORTH' },
  { id: 'C-0002', name: 'Ben Carter', email: 'ben@example.com', tier: 'STANDARD', region: 'SOUTH' },
  { id: 'C-0003', name: 'Asha Rao', email: 'asha@example.com', tier: 'SILVER', region: 'NORTH' },
];
const index = indexCustomers(customers);

const mk = (id: string, customerId: string, status: Order['status'], total: number, createdAt: string, skus: string[]): Order => ({
  id,
  customerId,
  status,
  total,
  createdAt,
  lines: skus.map((sku) => ({ sku, quantity: 1, unitPrice: total })),
});

const orders: Order[] = [
  mk('O-10001', 'C-0001', 'CREATED', 50, '2024-03-01T09:00:00Z', ['ELE-1001']),
  mk('O-10002', 'C-0002', 'PAID', 120.5, '2024-03-02T09:00:00Z', ['GRO-2001', 'GRO-2002']),
  mk('O-10003', 'C-0003', 'SHIPPED', 75, '2024-03-03T09:00:00Z', ['APP-3001']),
  mk('O-10004', 'C-0001', 'DELIVERED', 300, '2024-03-04T09:00:00Z', ['ELE-1003']),
  mk('O-10005', 'C-0002', 'CANCELLED', 75, '2024-03-05T09:00:00Z', ['TOY-5001']),
  mk('O-10006', 'C-9999', 'PAID', 10, '2024-03-06T09:00:00Z', ['HOM-4001']),
];

const ids = (list: Order[]) => list.map((o) => o.id.slice(-1)).join('');

describe('filterOrders', () => {
  it.each<[string, OrderFilters, string]>([
    ['no filters', {}, '123456'],
    ['ALL status and region', { status: 'ALL', region: 'ALL' }, '123456'],
    ['by status', { status: 'PAID' }, '26'],
    ['by region (unknown customers excluded)', { region: 'NORTH' }, '134'],
    ['by status and region', { status: 'SHIPPED', region: 'NORTH' }, '3'],
    ['by customer', { customerId: 'C-0001' }, '14'],
    ['by total range', { minTotal: 75, maxTotal: 200 }, '235'],
    ['by date range', { from: '2024-03-02', to: '2024-03-04' }, '234'],
    ['text matches order id', { text: 'o-10005' }, '5'],
    ['text matches customer name ignoring accents', { text: 'zoe' }, '14'],
    ['text matches sku', { text: 'gro-2002' }, '2'],
    ['text matches customer id', { text: 'C-0003' }, '3'],
    ['all text tokens must match', { text: 'ben gro' }, '2'],
    ['no match', { text: 'nothing' }, ''],
  ])('%s', (_name, filters, expected) => {
    expect(ids(filterOrders(orders, filters, index))).toBe(expected);
  });

  it('does not mutate its input', () => {
    const copy = [...orders];
    filterOrders(orders, { status: 'PAID' }, index);
    expect(orders).toEqual(copy);
  });
});

describe('sortOrders', () => {
  it.each<[SortSpec, string]>([
    [{ key: 'createdAt', direction: 'desc' }, '654321'],
    [{ key: 'createdAt', direction: 'asc' }, '123456'],
    [{ key: 'total', direction: 'asc' }, '613524'],
    [{ key: 'total', direction: 'desc' }, '423516'],
    [{ key: 'id', direction: 'desc' }, '654321'],
    [{ key: 'status', direction: 'asc' }, '126345'],
    [{ key: 'customer', direction: 'asc' }, '325614'],
  ])('%j -> %s', (sort, expected) => {
    expect(ids(sortOrders(orders, sort, index))).toBe(expected);
  });

  it('breaks ties by order id regardless of direction', () => {
    const tied = sortOrders(orders.filter((o) => o.total === 75), { key: 'total', direction: 'desc' }, index);
    expect(ids(tied)).toBe('35');
  });
});

describe('nextSort', () => {
  it.each<[SortSpec, SortSpec['key'], SortSpec]>([
    [{ key: 'total', direction: 'desc' }, 'total', { key: 'total', direction: 'asc' }],
    [{ key: 'total', direction: 'asc' }, 'total', { key: 'total', direction: 'desc' }],
    [{ key: 'total', direction: 'asc' }, 'id', { key: 'id', direction: 'asc' }],
    [{ key: 'id', direction: 'asc' }, 'createdAt', { key: 'createdAt', direction: 'desc' }],
    [{ key: 'id', direction: 'asc' }, 'customer', { key: 'customer', direction: 'asc' }],
  ])('from %j clicking %s', (current, key, expected) => {
    expect(nextSort(current, key)).toEqual(expected);
  });
});
