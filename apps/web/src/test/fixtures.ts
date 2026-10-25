/**
 * Deterministic sample data shared by component tests and the Playwright API mocks.
 * Order totals are computed with the real pricing rules so the UI and fixtures agree.
 */
import type { Customer, Order, OrderLine, OrderStatus, Product } from '../generated/schemas';
import { computeQuote } from '../lib/cart';

export const customers: Customer[] = [
  { id: 'C-0001', name: 'Asha Rao', email: 'asha.rao@example.com', tier: 'PLATINUM', region: 'NORTH' },
  { id: 'C-0002', name: 'Ben Carter', email: 'ben.carter@example.com', tier: 'STANDARD', region: 'SOUTH' },
  { id: 'C-0003', name: 'Chen Wei', email: 'chen.wei@example.com', tier: 'GOLD', region: 'EAST' },
  { id: 'C-0004', name: 'Divya Menon', email: 'divya.menon@example.com', tier: 'SILVER', region: 'WEST' },
  { id: 'C-0005', name: 'Elena Garcia', email: 'elena.garcia@example.com', tier: 'STANDARD', region: 'NORTH' },
  { id: 'C-0006', name: 'Farid Haddad', email: 'farid.haddad@example.com', tier: 'GOLD', region: 'SOUTH' },
  { id: 'C-0007', name: 'Grace Kim', email: 'grace.kim@example.com', tier: 'SILVER', region: 'EAST' },
  { id: 'C-0008', name: 'Hiro Tanaka', email: 'hiro.tanaka@example.com', tier: 'STANDARD', region: 'WEST' },
];

export const products: Product[] = [
  { id: 'P-01', sku: 'ELE-1001', name: 'Wireless Mouse', category: 'ELECTRONICS', unitPrice: 24.99, active: true },
  { id: 'P-02', sku: 'ELE-1002', name: 'USB-C Charger', category: 'ELECTRONICS', unitPrice: 39.5, active: true },
  { id: 'P-03', sku: 'ELE-1003', name: 'Noise Cancelling Headphones', category: 'ELECTRONICS', unitPrice: 199, active: true },
  { id: 'P-04', sku: 'GRO-2001', name: 'Organic Coffee Beans', category: 'GROCERY', unitPrice: 12.75, active: true },
  { id: 'P-05', sku: 'GRO-2002', name: 'Green Tea Box', category: 'GROCERY', unitPrice: 6.4, active: true },
  { id: 'P-06', sku: 'APP-3001', name: 'Cotton T-Shirt', category: 'APPAREL', unitPrice: 15, active: true },
  { id: 'P-07', sku: 'APP-3002', name: 'Rain Jacket', category: 'APPAREL', unitPrice: 89.95, active: true },
  { id: 'P-08', sku: 'HOM-4001', name: 'Ceramic Mug', category: 'HOME', unitPrice: 8.25, active: true },
  { id: 'P-09', sku: 'HOM-4002', name: 'Desk Lamp', category: 'HOME', unitPrice: 45, active: true },
  { id: 'P-10', sku: 'TOY-5001', name: 'Puzzle Cube', category: 'TOYS', unitPrice: 9.99, active: true },
  { id: 'P-11', sku: 'TOY-5002', name: 'Wooden Train Set', category: 'TOYS', unitPrice: 54.5, active: true },
  { id: 'P-12', sku: 'ELE-1004', name: 'Legacy Wired Mouse', category: 'ELECTRONICS', unitPrice: 9.5, active: false },
];

const STATUS_CYCLE: OrderStatus[] = ['CREATED', 'PAID', 'SHIPPED', 'DELIVERED', 'DELIVERED', 'CANCELLED', 'PAID'];
const COUPON_CYCLE: Array<string | undefined> = [undefined, 'SAVE10', undefined, 'FREESHIP', undefined];

/** 2024-03-01T09:00:00Z; orders are spread out every 13 hours after this instant. */
export const FIRST_ORDER_AT = Date.UTC(2024, 2, 1, 9, 0, 0);

export function priceOrder(customerId: string, lines: OrderLine[], couponCode?: string): number {
  const customer = customers.find((c) => c.id === customerId);
  if (!customer) throw new Error(`Unknown customer ${customerId}`);
  const input = { lines, tier: customer.tier, region: customer.region, ...(couponCode ? { couponCode } : {}) };
  return computeQuote(input).total;
}

function buildOrders(count: number): Order[] {
  const active = products.filter((p) => p.active);
  return Array.from({ length: count }, (_, i) => {
    const customer = customers[i % customers.length] as Customer;
    const lineCount = (i % 3) + 1;
    const lines: OrderLine[] = Array.from({ length: lineCount }, (_, j) => {
      const product = active[(i * 3 + j * 5) % active.length] as Product;
      return { sku: product.sku, quantity: ((i + j) % 4) + 1 + (i % 7 === 0 ? 10 : 0), unitPrice: product.unitPrice };
    });
    const couponCode = COUPON_CYCLE[i % COUPON_CYCLE.length];
    const order: Order = {
      id: `O-${String(10001 + i)}`,
      customerId: customer.id,
      status: STATUS_CYCLE[i % STATUS_CYCLE.length] as OrderStatus,
      lines,
      createdAt: new Date(FIRST_ORDER_AT + i * 13 * 3_600_000).toISOString(),
      total: priceOrder(customer.id, lines, couponCode),
    };
    if (couponCode) order.couponCode = couponCode;
    return order;
  });
}

/** 34 orders: enough for multiple pages at the default page size of 10. */
export const orders: Order[] = buildOrders(34);

/** "Now" used by tests that depend on the current date: one day after the last fixture order. */
export const FIXED_NOW = new Date(FIRST_ORDER_AT + 34 * 13 * 3_600_000);

export function cloneOrders(): Order[] {
  return orders.map((o) => ({ ...o, lines: o.lines.map((l) => ({ ...l })) }));
}

export function findOrder(id: string): Order {
  const order = orders.find((o) => o.id === id);
  if (!order) throw new Error(`No fixture order ${id}`);
  return order;
}

export function findCustomer(id: string): Customer {
  const customer = customers.find((c) => c.id === id);
  if (!customer) throw new Error(`No fixture customer ${id}`);
  return customer;
}
