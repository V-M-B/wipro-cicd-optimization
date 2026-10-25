import { describe, expect, it } from 'vitest';
import { DEFAULT_LIST_STATE, parseOrderListState, serializeOrderListState, updateListState } from './queryState';
import type { OrderListState } from './queryState';

const parse = (qs: string) => parseOrderListState(new URLSearchParams(qs));

describe('parseOrderListState', () => {
  it('returns defaults for an empty query', () => {
    expect(parse('')).toEqual(DEFAULT_LIST_STATE);
  });

  it('reads every supported parameter', () => {
    expect(parse('status=PAID&region=EAST&q=%20asha%20&sort=total&dir=asc&page=3&size=25')).toEqual({
      status: 'PAID',
      region: 'EAST',
      text: 'asha',
      sort: { key: 'total', direction: 'asc' },
      page: 3,
      pageSize: 25,
    });
  });

  it.each([
    ['status=paid', 'status', 'ALL'],
    ['status=UNKNOWN', 'status', 'ALL'],
    ['region=CENTRAL', 'region', 'ALL'],
    ['page=0', 'page', 1],
    ['page=-4', 'page', 1],
    ['page=abc', 'page', 1],
    ['page=2.5', 'page', 1],
    ['size=30', 'pageSize', 10],
    ['size=50', 'pageSize', 50],
  ] as const)('%s -> %s=%j', (qs, key, expected) => {
    expect(parse(qs)[key]).toBe(expected);
  });

  it.each([
    ['sort=total', { key: 'total', direction: 'asc' }],
    ['sort=createdAt', { key: 'createdAt', direction: 'desc' }],
    ['sort=bogus&dir=asc', { key: 'createdAt', direction: 'asc' }],
    ['sort=id&dir=sideways', { key: 'id', direction: 'asc' }],
  ])('%s -> %j', (qs, expected) => {
    expect(parse(qs).sort).toEqual(expected);
  });
});

describe('serializeOrderListState', () => {
  it('omits defaults', () => {
    expect(serializeOrderListState(DEFAULT_LIST_STATE).toString()).toBe('');
  });

  it.each<[Partial<OrderListState>, string]>([
    [{ status: 'SHIPPED' }, 'status=SHIPPED'],
    [{ region: 'WEST', text: '  ben ' }, 'region=WEST&q=ben'],
    [{ sort: { key: 'total', direction: 'desc' } }, 'sort=total&dir=desc'],
    [{ page: 2, pageSize: 50 }, 'page=2&size=50'],
  ])('%j -> %s', (patch, expected) => {
    expect(serializeOrderListState({ ...DEFAULT_LIST_STATE, ...patch }).toString()).toBe(expected);
  });

  it('round-trips through the URL', () => {
    const state: OrderListState = {
      status: 'DELIVERED',
      region: 'SOUTH',
      text: 'gro-2001',
      sort: { key: 'customer', direction: 'desc' },
      page: 4,
      pageSize: 25,
    };
    expect(parseOrderListState(serializeOrderListState(state))).toEqual(state);
  });
});

describe('updateListState', () => {
  const onPage3 = { ...DEFAULT_LIST_STATE, page: 3 };

  it('resets to page 1 when a filter changes', () => {
    expect(updateListState(onPage3, { status: 'PAID' }).page).toBe(1);
  });

  it('keeps the requested page for page-only changes', () => {
    expect(updateListState(onPage3, { page: 2 }).page).toBe(2);
  });

  it('honours an explicit page alongside other changes', () => {
    expect(updateListState(onPage3, { page: 2, text: 'x' })).toMatchObject({ page: 2, text: 'x' });
  });
});
