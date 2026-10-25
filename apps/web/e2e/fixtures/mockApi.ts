/**
 * In-memory backend for e2e tests. Every request to /api/** is fulfilled by `page.route`; nothing
 * leaves the browser. Each test gets a fresh copy of the deterministic fixture data, so tests are
 * independent and can run in parallel.
 */
import { test as base, expect } from '@playwright/test';
import type { Page, Route } from '@playwright/test';
import type { Customer, Order, OrderStatus, Product } from '../../src/generated/schemas';
import { computeQuote, toPriceQuote } from '../../src/lib/cart';
import { canTransition } from '../../src/lib/orderStatus';
import { FIXED_NOW, cloneOrders, customers as fixtureCustomers, products as fixtureProducts } from '../../src/test/fixtures';

interface CreateBody {
  customerId: string;
  lines: Array<{ sku: string; quantity: number }>;
  couponCode?: string;
}

export interface RecordedRequest {
  method: string;
  path: string;
  body: unknown;
}

export class MockBackend {
  orders: Order[] = cloneOrders();
  readonly customers: Customer[] = fixtureCustomers.map((c) => ({ ...c }));
  readonly products: Product[] = fixtureProducts.map((p) => ({ ...p }));
  readonly requests: RecordedRequest[] = [];
  private readonly failures: Array<{ method: string; path: RegExp; status: number; body: unknown; times: number }> = [];
  private nextId = 20001;

  /** Make the next `times` matching requests fail with `status`. */
  fail(method: string, path: RegExp, status: number, body: unknown = { message: `Mock failure ${status}` }, times = 1): void {
    this.failures.push({ method, path, status, body, times });
  }

  async handle(route: Route): Promise<void> {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname;
    const body = request.postData() ? (JSON.parse(request.postData() as string) as unknown) : undefined;
    this.requests.push({ method, path, body });

    const failure = this.failures.find((f) => f.method === method && f.path.test(path) && f.times > 0);
    if (failure) {
      failure.times -= 1;
      return route.fulfill({ status: failure.status, json: failure.body });
    }

    const [, , resource, id] = path.split('/');
    if (resource === 'orders') return this.handleOrders(route, method, id, url.searchParams, body);
    if (resource === 'products' && method === 'GET') return route.fulfill({ json: this.products });
    if (resource === 'customers' && method === 'GET') {
      if (!id) return route.fulfill({ json: this.customers });
      const customer = this.customers.find((c) => c.id === id);
      return customer ? route.fulfill({ json: customer }) : route.fulfill({ status: 404, json: { message: 'Customer not found' } });
    }
    if (resource === 'quotes' && method === 'POST') return this.quote(route, body as CreateBody);
    return route.fulfill({ status: 404, json: { message: `No mock for ${method} ${path}` } });
  }

  private async handleOrders(route: Route, method: string, id: string | undefined, query: URLSearchParams, body: unknown) {
    if (!id && method === 'GET') {
      const status = query.get('status');
      return route.fulfill({ json: status ? this.orders.filter((o) => o.status === status) : this.orders });
    }
    if (!id && method === 'POST') return this.create(route, body as CreateBody);
    const order = this.orders.find((o) => o.id === decodeURIComponent(id ?? ''));
    if (!order) return route.fulfill({ status: 404, json: { message: 'Order not found' } });
    if (method === 'GET') return route.fulfill({ json: order });
    if (method === 'PATCH') {
      const next = (body as { status: OrderStatus }).status;
      if (!canTransition(order.status, next)) {
        return route.fulfill({ status: 409, json: { message: `Cannot move an order from ${order.status} to ${next}` } });
      }
      order.status = next;
      return route.fulfill({ json: order });
    }
    return route.fulfill({ status: 405, json: { message: 'Method not allowed' } });
  }

  private priced(request: CreateBody) {
    const customer = this.customers.find((c) => c.id === request.customerId);
    if (!customer) return null;
    const lines = request.lines.map((l) => ({
      sku: l.sku,
      quantity: l.quantity,
      unitPrice: this.products.find((p) => p.sku === l.sku)?.unitPrice ?? 0,
    }));
    const quote = computeQuote({
      lines,
      tier: customer.tier,
      region: customer.region,
      ...(request.couponCode ? { couponCode: request.couponCode } : {}),
    });
    return { lines, quote };
  }

  private async quote(route: Route, request: CreateBody) {
    const priced = this.priced(request);
    if (!priced) return route.fulfill({ status: 422, json: { message: 'Unknown customer' } });
    return route.fulfill({ json: toPriceQuote(priced.quote) });
  }

  private async create(route: Route, request: CreateBody) {
    const priced = this.priced(request);
    if (!priced) return route.fulfill({ status: 422, json: { message: 'Unknown customer' } });
    const order: Order = {
      id: `O-${this.nextId++}`,
      customerId: request.customerId,
      status: 'CREATED',
      lines: priced.lines,
      createdAt: FIXED_NOW.toISOString(),
      total: priced.quote.total,
    };
    if (request.couponCode) order.couponCode = request.couponCode;
    this.orders.push(order);
    return route.fulfill({ status: 201, json: order });
  }
}

async function install(page: Page, backend: MockBackend) {
  await page.clock.setFixedTime(FIXED_NOW);
  await page.route('**/api/**', (route) => backend.handle(route));
}

export const test = base.extend<{ backend: MockBackend }>({
  backend: [
    async ({ page }, use) => {
      const backend = new MockBackend();
      await install(page, backend);
      await use(backend);
    },
    { auto: true },
  ],
});

export { expect };
