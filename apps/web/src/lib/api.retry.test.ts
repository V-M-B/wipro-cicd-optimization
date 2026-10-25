// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { ApiClient, backoffDelay, parseRetryAfter } from './api';
import type { FetchLike } from './api';

const status = (code: number, headers: Record<string, string> = {}) => new Response('', { status: code, headers });
const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

function setup(responses: Array<Response | Error>, retries?: number) {
  const fetchImpl = vi.fn<FetchLike>(async () => {
    const next = responses.shift();
    if (!next) throw new Error('unexpected request');
    if (next instanceof Error) throw next;
    return next;
  });
  const sleep = vi.fn(async (_ms: number) => undefined);
  const api = new ApiClient({ fetchImpl, sleep, retryDelayMs: 100, ...(retries === undefined ? {} : { retries }) });
  return { api, fetchImpl, sleep };
}

describe('retry policy', () => {
  it('retries a GET after 503 and succeeds', async () => {
    const { api, fetchImpl, sleep } = setup([status(503), ok([1])]);
    await expect(api.listOrders()).resolves.toEqual([1]);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(sleep).toHaveBeenCalledWith(100);
  });

  it('retries network failures with exponential backoff', async () => {
    const { api, fetchImpl, sleep } = setup([new TypeError('Failed to fetch'), new TypeError('Failed to fetch'), ok([])]);
    await api.listProducts();
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(sleep.mock.calls.map((c) => c[0])).toEqual([100, 200]);
  });

  it('gives up after the configured retries and throws the last error', async () => {
    const { api, fetchImpl } = setup([status(502), status(503), status(504)]);
    await expect(api.listCustomers()).rejects.toMatchObject({ kind: 'unavailable', status: 504 });
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it('honours retries: 0', async () => {
    const { api, fetchImpl } = setup([status(503)], 0);
    await expect(api.listCustomers()).rejects.toMatchObject({ kind: 'unavailable' });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it('never retries non-idempotent requests', async () => {
    const { api, fetchImpl } = setup([status(503)]);
    await expect(api.createOrder({ customerId: 'C-0001', lines: [] })).rejects.toMatchObject({ kind: 'unavailable' });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it.each([400, 404, 422, 500])('does not retry HTTP %d', async (code) => {
    const { api, fetchImpl, sleep } = setup([status(code)]);
    await expect(api.listOrders()).rejects.toMatchObject({ status: code });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });

  it('waits for Retry-After on 429', async () => {
    const { api, sleep } = setup([status(429, { 'Retry-After': '2' }), ok([])]);
    await api.listOrders();
    expect(sleep).toHaveBeenCalledWith(2000);
  });
});

describe('backoffDelay', () => {
  it.each([
    [0, 100, 5000, 100],
    [1, 100, 5000, 200],
    [3, 100, 5000, 800],
    [10, 100, 5000, 5000],
    [2, 250, 600, 600],
  ])('attempt %d base %d max %d -> %d', (attempt, base, max, expected) => {
    expect(backoffDelay(attempt, base, max)).toBe(expected);
  });
});

describe('parseRetryAfter', () => {
  it.each([
    ['3', 3000],
    ['120', 10000],
    ['Wed, 21 Oct 2015 07:28:00 GMT', undefined],
    [null, undefined],
  ])('parseRetryAfter(%j) = %j', (header, expected) => {
    expect(parseRetryAfter(header)).toBe(expected);
  });
});
