import { OrderStatusValues, RegionValues } from '../generated/schemas';
import type { Customer, Order, OrderStatus, Region } from '../generated/schemas';
import { lastNDays, toIsoDate } from './dates';
import { roundHalfEven, sumMoney } from './money';
import type { CustomerIndex } from './orderQuery';

/** Orders that represent booked revenue (paid and beyond, not cancelled). */
export const REVENUE_STATUSES: ReadonlySet<OrderStatus> = new Set<OrderStatus>(['PAID', 'SHIPPED', 'DELIVERED']);

export function isRevenueOrder(order: Order): boolean {
  return REVENUE_STATUSES.has(order.status);
}

export function totalRevenue(orders: readonly Order[]): number {
  return sumMoney(orders.filter(isRevenueOrder).map((o) => o.total));
}

export function averageOrderValue(orders: readonly Order[]): number {
  const revenueOrders = orders.filter(isRevenueOrder);
  if (revenueOrders.length === 0) return 0;
  return roundHalfEven(totalRevenue(revenueOrders) / revenueOrders.length, 2);
}

export function countByStatus(orders: readonly Order[]): Record<OrderStatus, number> {
  const counts = Object.fromEntries(OrderStatusValues.map((s) => [s, 0])) as Record<OrderStatus, number>;
  for (const order of orders) counts[order.status] += 1;
  return counts;
}

export function revenueByRegion(orders: readonly Order[], customers: CustomerIndex): Record<Region, number> {
  const buckets = Object.fromEntries(RegionValues.map((r) => [r, [] as number[]])) as Record<Region, number[]>;
  for (const order of orders.filter(isRevenueOrder)) {
    const region = customers.get(order.customerId)?.region;
    if (region) buckets[region].push(order.total);
  }
  return Object.fromEntries(RegionValues.map((r) => [r, sumMoney(buckets[r])])) as Record<Region, number>;
}

/** Share of non-cancelled orders that have been delivered (0..1). */
export function fulfillmentRate(orders: readonly Order[]): number {
  const active = orders.filter((o) => o.status !== 'CANCELLED');
  if (active.length === 0) return 0;
  return active.filter((o) => o.status === 'DELIVERED').length / active.length;
}

export function cancellationRate(orders: readonly Order[]): number {
  if (orders.length === 0) return 0;
  return orders.filter((o) => o.status === 'CANCELLED').length / orders.length;
}

export interface SkuVolume {
  sku: string;
  quantity: number;
  /** Share of all units sold (0..1), across every SKU and not just the ones returned. */
  share: number;
}

/** Best-selling SKUs by units across non-cancelled orders; ties broken by SKU. */
export function topSkus(orders: readonly Order[], limit = 5): SkuVolume[] {
  const volume = new Map<string, number>();
  let totalUnits = 0;
  for (const order of orders) {
    if (order.status === 'CANCELLED') continue;
    for (const line of order.lines) {
      volume.set(line.sku, (volume.get(line.sku) ?? 0) + line.quantity);
      totalUnits += line.quantity;
    }
  }
  return [...volume.entries()]
    .map(([sku, quantity]) => ({ sku, quantity, share: totalUnits === 0 ? 0 : quantity / totalUnits }))
    .sort((a, b) => b.quantity - a.quantity || a.sku.localeCompare(b.sku, 'en'))
    .slice(0, limit);
}

export interface DailyCount {
  date: string;
  count: number;
}

/** Orders created on each of the `days` days ending at `now` (UTC), oldest first. */
export function ordersPerDay(orders: readonly Order[], now: Date, days = 7): DailyCount[] {
  const range = lastNDays(now, days);
  const counts = new Map(range.map((d) => [d, 0]));
  for (const order of orders) {
    const day = toIsoDate(new Date(order.createdAt));
    if (counts.has(day)) counts.set(day, (counts.get(day) ?? 0) + 1);
  }
  return range.map((date) => ({ date, count: counts.get(date) ?? 0 }));
}

export interface CustomerStats {
  orderCount: number;
  lifetimeValue: number;
}

export function customerStats(orders: readonly Order[]): Map<string, CustomerStats> {
  const stats = new Map<string, { orderCount: number; totals: number[] }>();
  for (const order of orders) {
    const entry = stats.get(order.customerId) ?? { orderCount: 0, totals: [] };
    entry.orderCount += 1;
    if (isRevenueOrder(order)) entry.totals.push(order.total);
    stats.set(order.customerId, entry);
  }
  return new Map(
    [...stats.entries()].map(([id, s]) => [id, { orderCount: s.orderCount, lifetimeValue: sumMoney(s.totals) }]),
  );
}

export interface DashboardKpis {
  revenue: number;
  orderCount: number;
  averageOrderValue: number;
  fulfillmentRate: number;
  cancellationRate: number;
  openOrders: number;
  byStatus: Record<OrderStatus, number>;
  byRegion: Record<Region, number>;
  topSkus: SkuVolume[];
  last7Days: DailyCount[];
}

export function computeDashboard(orders: readonly Order[], customers: readonly Customer[], now: Date): DashboardKpis {
  const index = new Map(customers.map((c) => [c.id, c]));
  const byStatus = countByStatus(orders);
  return {
    revenue: totalRevenue(orders),
    orderCount: orders.length,
    averageOrderValue: averageOrderValue(orders),
    fulfillmentRate: fulfillmentRate(orders),
    cancellationRate: cancellationRate(orders),
    openOrders: byStatus.CREATED + byStatus.PAID + byStatus.SHIPPED,
    byStatus,
    byRegion: revenueByRegion(orders, index),
    topSkus: topSkus(orders),
    last7Days: ordersPerDay(orders, now, 7),
  };
}
