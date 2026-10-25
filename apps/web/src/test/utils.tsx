import { render } from '@testing-library/react';
import type { RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { vi } from 'vitest';
import type { Mock } from 'vitest';
import { ApiProvider } from '../api/ApiProvider';
import { ApiError } from '../lib/api';
import type { RetailApi } from '../lib/api';
import { computeQuote, toPriceQuote } from '../lib/cart';
import { cloneOrders, customers, products } from './fixtures';

export type MockApi = { [K in keyof RetailApi]: Mock<RetailApi[K]> };

/** A RetailApi whose methods are vi.fn()s backed by the deterministic fixtures. */
export function createMockApi(overrides: Partial<RetailApi> = {}): MockApi {
  const orders = cloneOrders();
  const api: MockApi = {
    listOrders: vi.fn(async () => orders),
    getOrder: vi.fn(async (id: string) => {
      const order = orders.find((o) => o.id === id);
      if (!order) throw new ApiError('not_found', 'Order not found', 404);
      return order;
    }),
    createOrder: vi.fn(async (request) => ({
      id: 'O-20001',
      customerId: request.customerId,
      status: 'CREATED' as const,
      lines: request.lines.map((l) => ({
        ...l,
        unitPrice: products.find((p) => p.sku === l.sku)?.unitPrice ?? 0,
      })),
      createdAt: '2024-03-20T10:00:00.000Z',
      total: 0,
    })),
    updateOrderStatus: vi.fn(async (id, status) => {
      const order = orders.find((o) => o.id === id);
      if (!order) throw new ApiError('not_found', 'Order not found', 404);
      return { ...order, status };
    }),
    listProducts: vi.fn(async () => products),
    listCustomers: vi.fn(async () => customers),
    getCustomer: vi.fn(async (id: string) => {
      const customer = customers.find((c) => c.id === id);
      if (!customer) throw new ApiError('not_found', 'Customer not found', 404);
      return customer;
    }),
    getQuote: vi.fn(async (request) => {
      const customer = customers.find((c) => c.id === request.customerId);
      if (!customer) throw new ApiError('validation', 'Unknown customer', 422);
      const lines = request.lines.map((l) => ({
        ...l,
        unitPrice: products.find((p) => p.sku === l.sku)?.unitPrice ?? 0,
      }));
      return toPriceQuote(
        computeQuote({
          lines,
          tier: customer.tier,
          region: customer.region,
          ...(request.couponCode ? { couponCode: request.couponCode } : {}),
        }),
      );
    }),
  };
  for (const [key, impl] of Object.entries(overrides)) {
    (api as Record<string, Mock>)[key] = vi.fn(impl as (...args: unknown[]) => unknown);
  }
  return api;
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{`${location.pathname}${location.search}`}</div>;
}

export interface RenderOptions {
  api?: RetailApi;
  /** Initial URL, e.g. `/orders?status=PAID`. */
  route?: string;
  /** Route pattern the element is mounted at, e.g. `/orders/:orderId`. */
  path?: string;
  /** Extra routes (e.g. navigation targets). */
  extraRoutes?: Array<{ path: string; element: ReactElement }>;
}

export function renderWithProviders(
  ui: ReactElement,
  { api = createMockApi(), route = '/', path = '*', extraRoutes = [] }: RenderOptions = {},
): RenderResult & { api: RetailApi; user: ReturnType<typeof userEvent.setup> } {
  const user = userEvent.setup();
  const result = render(
    <ApiProvider api={api}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
          {extraRoutes.map((r) => (
            <Route key={r.path} path={r.path} element={r.element} />
          ))}
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </ApiProvider>,
  );
  return { ...result, api, user };
}
