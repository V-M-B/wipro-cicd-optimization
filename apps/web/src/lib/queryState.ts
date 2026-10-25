import { OrderStatusValues, RegionValues } from '../generated/schemas';
import type { OrderStatus, Region } from '../generated/schemas';
import { DEFAULT_SORT } from './orderQuery';
import type { SortDirection, SortKey, SortSpec } from './orderQuery';

/** Order-list view state, round-tripped through the URL query string so views are shareable. */
export interface OrderListState {
  status: OrderStatus | 'ALL';
  region: Region | 'ALL';
  text: string;
  sort: SortSpec;
  page: number;
  pageSize: number;
}

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;

export const DEFAULT_LIST_STATE: OrderListState = {
  status: 'ALL',
  region: 'ALL',
  text: '',
  sort: DEFAULT_SORT,
  page: 1,
  pageSize: 10,
};

const SORT_KEYS: readonly SortKey[] = ['createdAt', 'total', 'id', 'status', 'customer'];

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | undefined {
  return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : undefined;
}

function positiveInt(value: string | null): number | undefined {
  if (value === null || !/^\d+$/.test(value)) return undefined;
  const n = Number(value);
  return n >= 1 ? n : undefined;
}

export function parseOrderListState(params: URLSearchParams): OrderListState {
  const status = oneOf(params.get('status'), OrderStatusValues) ?? DEFAULT_LIST_STATE.status;
  const region = oneOf(params.get('region'), RegionValues) ?? DEFAULT_LIST_STATE.region;
  const text = (params.get('q') ?? '').trim();
  const key = oneOf(params.get('sort'), SORT_KEYS) ?? DEFAULT_SORT.key;
  const direction =
    oneOf<SortDirection>(params.get('dir'), ['asc', 'desc']) ??
    (key === DEFAULT_SORT.key ? DEFAULT_SORT.direction : 'asc');
  const page = positiveInt(params.get('page')) ?? 1;
  const sizeParam = positiveInt(params.get('size'));
  const pageSize = (PAGE_SIZE_OPTIONS as readonly number[]).includes(sizeParam ?? -1)
    ? (sizeParam as number)
    : DEFAULT_LIST_STATE.pageSize;
  return { status, region, text, sort: { key, direction }, page, pageSize };
}

/** Serialise state, omitting values equal to the defaults so URLs stay short. */
export function serializeOrderListState(state: OrderListState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.status !== 'ALL') params.set('status', state.status);
  if (state.region !== 'ALL') params.set('region', state.region);
  if (state.text.trim() !== '') params.set('q', state.text.trim());
  if (state.sort.key !== DEFAULT_SORT.key || state.sort.direction !== DEFAULT_SORT.direction) {
    params.set('sort', state.sort.key);
    params.set('dir', state.sort.direction);
  }
  if (state.page > 1) params.set('page', String(state.page));
  if (state.pageSize !== DEFAULT_LIST_STATE.pageSize) params.set('size', String(state.pageSize));
  return params;
}

/** Apply a partial update; any change other than the page itself resets to page 1. */
export function updateListState(state: OrderListState, patch: Partial<OrderListState>): OrderListState {
  const next = { ...state, ...patch };
  const onlyPage = Object.keys(patch).every((k) => k === 'page');
  if (!onlyPage) next.page = patch.page ?? 1;
  return next;
}
