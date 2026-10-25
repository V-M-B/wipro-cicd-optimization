// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { ApiClient, ApiError, buildQuery } from './api';
import type { FetchLike } from './api';

const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });

function client(responses: Array<Response | Error>, baseUrl = '') {
  const fetchImpl = vi.fn<FetchLike>(async () => {
    const next = responses.shift();
    if (!next) throw new Error('unexpected request');
    if (next instanceof Error) throw next;
    return next;
  });
  const sleep = vi.fn(async () => undefined);
  return { api: new ApiClient({ baseUrl, fetchImpl, sleep }), fetchImpl, sleep };
}

describe('buildQuery', () => {
  it.each([
    [{}, ''],
    [{ status: 'PAID' }, '?status=PAID'],
    [{ b: 2, a: 1 }, '?a=1&b=2'],
    [{ a: undefined, b: null, c: '' }, ''],
    [{ q: 'a b&c' }, '?q=a+b%26c'],
    [{ flag: true }, '?flag=true'],
  ])('buildQuery(%j) = %j', (params, expected) => {
    expect(buildQuery(params)).toBe(expected);
  });
});

describe('ApiClient requests', () => {
  it('lists orders with sorted query parameters', async () => {
    const { api, fetchImpl } = client([json([])]);
    await expect(api.listOrders({ status: 'PAID', customerId: 'C-0001' })).resolves.toEqual([]);
    expect(fetchImpl).toHaveBeenCalledWith('/api/orders?customerId=C-0001&status=PAID', expect.objectContaining({ method: 'GET' }));
  });

  it('prefixes the base URL without doubling slashes', async () => {
    const { api, fetchImpl } = client([json([])], 'https://shop.test/');
    await api.listProducts();
    expect(fetchImpl.mock.calls[0]?.[0]).toBe('https://shop.test/api/products');
  });

  it('encodes path parameters', async () => {
    const { api, fetchImpl } = client([json({ id: 'O/1' })]);
    await api.getOrder('O/1 x');
    expect(fetchImpl.mock.calls[0]?.[0]).toBe('/api/orders/O%2F1%20x');
  });

  it('posts JSON when creating an order', async () => {
    const created = { id: 'O-20001' };
    const { api, fetchImpl } = client([json(created, 201)]);
    const request = { customerId: 'C-0001', lines: [{ sku: 'ELE-1001', quantity: 2 }] };
    await expect(api.createOrder(request)).resolves.toEqual(created);
    const init = fetchImpl.mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.headers).toMatchObject({ 'Content-Type': 'application/json', Accept: 'application/json' });
    expect(JSON.parse(String(init?.body))).toEqual(request);
  });

  it('patches the status of an order', async () => {
    const { api, fetchImpl } = client([json({ id: 'O-10001', status: 'PAID' })]);
    await api.updateOrderStatus('O-10001', 'PAID');
    expect(fetchImpl.mock.calls[0]?.[0]).toBe('/api/orders/O-10001');
    expect(fetchImpl.mock.calls[0]?.[1]).toMatchObject({ method: 'PATCH', body: '{"status":"PAID"}' });
  });

  it('requests a quote', async () => {
    const quote = { subtotal: 10, discount: 0, tax: 0.8, shipping: 7.99, total: 18.79 };
    const { api, fetchImpl } = client([json(quote)]);
    await expect(api.getQuote({ customerId: 'C-0001', lines: [{ sku: 'ELE-1001', quantity: 1 }] })).resolves.toEqual(quote);
    expect(fetchImpl.mock.calls[0]?.[0]).toBe('/api/quotes');
  });

  it.each([
    ['listCustomers', () => [] as const, '/api/customers'],
    ['getCustomer', () => ['C-0002'] as const, '/api/customers/C-0002'],
    ['listProducts', () => [] as const, '/api/products'],
  ] as const)('%s calls %s', async (method, args, url) => {
    const { api, fetchImpl } = client([json([])]);
    await (api[method] as (...a: unknown[]) => Promise<unknown>)(...args());
    expect(fetchImpl.mock.calls[0]?.[0]).toBe(url);
  });

  it('forwards an AbortSignal', async () => {
    const controller = new AbortController();
    const { api, fetchImpl } = client([json([])]);
    await api.listCustomers(controller.signal);
    expect(fetchImpl.mock.calls[0]?.[1]?.signal).toBe(controller.signal);
  });

  it('returns undefined for 204 and empty bodies', async () => {
    const { api } = client([new Response(null, { status: 204 }), new Response('', { status: 200 })]);
    await expect(api.request('DELETE', '/api/orders/O-1')).resolves.toBeUndefined();
    await expect(api.request('GET', '/api/ping')).resolves.toBeUndefined();
  });

  it('raises a parse error for malformed JSON', async () => {
    const { api } = client([new Response('{not json', { status: 200 })]);
    await expect(api.listOrders()).rejects.toMatchObject({ kind: 'parse', status: 200 });
  });

  it('turns an aborted fetch into an aborted error without retrying', async () => {
    const abort = new Error('aborted');
    abort.name = 'AbortError';
    const { api, fetchImpl } = client([abort]);
    await expect(api.listOrders()).rejects.toBeInstanceOf(ApiError);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });
});
