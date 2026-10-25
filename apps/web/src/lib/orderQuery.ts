import type { Customer, Order, OrderStatus, Region } from '../generated/schemas';
import { isWithinDateRange } from './dates';
import { LIFECYCLE } from './orderStatus';
import { normalizeText } from './search';

export type CustomerIndex = ReadonlyMap<string, Customer>;

export function indexCustomers(customers: readonly Customer[]): Map<string, Customer> {
  return new Map(customers.map((c) => [c.id, c]));
}

export interface OrderFilters {
  status?: OrderStatus | 'ALL';
  region?: Region | 'ALL';
  customerId?: string;
  minTotal?: number;
  maxTotal?: number;
  /** Inclusive `YYYY-MM-DD`. */
  from?: string;
  /** Inclusive `YYYY-MM-DD`. */
  to?: string;
  /** Free text matched against order id, customer name and SKUs. */
  text?: string;
}

export function filterOrders(
  orders: readonly Order[],
  filters: OrderFilters,
  customers: CustomerIndex = new Map(),
): Order[] {
  const text = normalizeText(filters.text ?? '');
  return orders.filter((order) => {
    if (filters.status && filters.status !== 'ALL' && order.status !== filters.status) return false;
    if (filters.region && filters.region !== 'ALL') {
      const customer = customers.get(order.customerId);
      if (!customer || customer.region !== filters.region) return false;
    }
    if (filters.customerId && order.customerId !== filters.customerId) return false;
    if (filters.minTotal !== undefined && order.total < filters.minTotal) return false;
    if (filters.maxTotal !== undefined && order.total > filters.maxTotal) return false;
    if ((filters.from || filters.to) && !isWithinDateRange(order.createdAt, filters.from, filters.to)) return false;
    if (text !== '') {
      const customerName = customers.get(order.customerId)?.name ?? '';
      const haystack = normalizeText([order.id, order.customerId, customerName, ...order.lines.map((l) => l.sku)].join(' '));
      if (!text.split(' ').every((token) => haystack.includes(token))) return false;
    }
    return true;
  });
}

export type SortKey = 'createdAt' | 'total' | 'id' | 'status' | 'customer';
export type SortDirection = 'asc' | 'desc';

export interface SortSpec {
  key: SortKey;
  direction: SortDirection;
}

export const DEFAULT_SORT: SortSpec = { key: 'createdAt', direction: 'desc' };

function statusRank(status: OrderStatus): number {
  const idx = LIFECYCLE.indexOf(status);
  return idx === -1 ? LIFECYCLE.length : idx;
}

function compareBy(key: SortKey, customers: CustomerIndex): (a: Order, b: Order) => number {
  switch (key) {
    case 'createdAt':
      return (a, b) => Date.parse(a.createdAt) - Date.parse(b.createdAt);
    case 'total':
      return (a, b) => a.total - b.total;
    case 'id':
      return (a, b) => a.id.localeCompare(b.id, 'en');
    case 'status':
      return (a, b) => statusRank(a.status) - statusRank(b.status);
    case 'customer':
      return (a, b) =>
        (customers.get(a.customerId)?.name ?? a.customerId).localeCompare(
          customers.get(b.customerId)?.name ?? b.customerId,
          'en',
        );
  }
}

/** Stable sort; ties are broken by order id ascending so output is deterministic. */
export function sortOrders(orders: readonly Order[], sort: SortSpec, customers: CustomerIndex = new Map()): Order[] {
  const cmp = compareBy(sort.key, customers);
  const sign = sort.direction === 'asc' ? 1 : -1;
  return [...orders].sort((a, b) => sign * cmp(a, b) || a.id.localeCompare(b.id, 'en'));
}

/** Toggle direction when clicking the active column; new columns start descending for numbers/dates. */
export function nextSort(current: SortSpec, key: SortKey): SortSpec {
  if (current.key === key) {
    return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' };
  }
  return { key, direction: key === 'createdAt' || key === 'total' ? 'desc' : 'asc' };
}

export interface Page<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  /** 1-based index of the first item on the page (0 if empty). */
  start: number;
  /** 1-based index of the last item on the page (0 if empty). */
  end: number;
}

export function paginate<T>(items: readonly T[], page: number, pageSize: number): Page<T> {
  if (!Number.isInteger(pageSize) || pageSize < 1) {
    throw new RangeError(`pageSize must be a positive integer: ${pageSize}`);
  }
  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.min(Math.max(1, Math.floor(Number.isFinite(page) ? page : 1)), totalPages);
  const offset = (safePage - 1) * pageSize;
  const slice = items.slice(offset, offset + pageSize);
  return {
    items: slice,
    page: safePage,
    pageSize,
    totalItems,
    totalPages,
    start: slice.length ? offset + 1 : 0,
    end: offset + slice.length,
  };
}

export type PageToken = number | 'ellipsis';

/**
 * Page numbers to render in a pager: always first and last, a window of `siblings` around
 * the current page, and 'ellipsis' markers for gaps larger than one page.
 */
export function pageWindow(current: number, totalPages: number, siblings = 1): PageToken[] {
  if (totalPages <= 0) return [];
  const pages = new Set<number>([1, totalPages]);
  for (let p = current - siblings; p <= current + siblings; p += 1) {
    if (p >= 1 && p <= totalPages) pages.add(p);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const tokens: PageToken[] = [];
  sorted.forEach((p, i) => {
    const prev = sorted[i - 1];
    if (prev !== undefined) {
      if (p - prev === 2) tokens.push(prev + 1);
      else if (p - prev > 2) tokens.push('ellipsis');
    }
    tokens.push(p);
  });
  return tokens;
}
