// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { ApiClient, ApiError, defaultMessage, errorMessage, isRetryableKind, mapStatusToKind } from './api';
import type { ApiErrorKind, FetchLike } from './api';

describe('mapStatusToKind', () => {
  it.each<[number, ApiErrorKind]>([
    [400, 'bad_request'],
    [401, 'unauthorized'],
    [404, 'not_found'],
    [409, 'conflict'],
    [422, 'validation'],
    [429, 'rate_limited'],
    [500, 'server'],
    [502, 'unavailable'],
    [504, 'unavailable'],
    [418, 'unknown'],
  ])('%d -> %s', (status, kind) => {
    expect(mapStatusToKind(status)).toBe(kind);
  });
});

describe('isRetryableKind', () => {
  it.each<[ApiErrorKind, boolean]>([
    ['network', true],
    ['unavailable', true],
    ['rate_limited', true],
    ['server', false],
    ['not_found', false],
  ])('%s -> %s', (kind, expected) => {
    expect(isRetryableKind(kind)).toBe(expected);
    expect(new ApiError(kind, 'x').retryable).toBe(expected);
  });
});

describe('error bodies', () => {
  const fail = (response: Response) => {
    const fetchImpl = vi.fn<FetchLike>(async () => response);
    return new ApiClient({ fetchImpl, retries: 0 });
  };

  it('uses the server message and field errors', async () => {
    const api = fail(
      new Response(JSON.stringify({ message: 'Order is invalid', errors: { 'lines[0].quantity': 'must be >= 1', sku: 42 } }), {
        status: 422,
      }),
    );
    const error = await api.createOrder({ customerId: 'C-0001', lines: [] }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      kind: 'validation',
      status: 422,
      message: 'Order is invalid',
      details: { 'lines[0].quantity': 'must be >= 1', sku: '42' },
    });
  });

  it('reads the detail of an RFC 7807 problem response', async () => {
    const problem = {
      type: 'https://retailops.example/problems/not-found',
      title: 'Resource not found',
      status: 404,
      detail: 'Order O-10001 not found',
    };
    const api = fail(new Response(JSON.stringify(problem), { status: 404 }));
    await expect(api.getOrder('O-10001')).rejects.toMatchObject({ kind: 'not_found', message: 'Order O-10001 not found' });
  });

  it('prefers the problem detail over a legacy message field', async () => {
    const api = fail(new Response(JSON.stringify({ detail: 'From detail', message: 'From message' }), { status: 409 }));
    await expect(api.getOrder('O-10001')).rejects.toMatchObject({ message: 'From detail' });
  });

  it('falls back to a default message for non-JSON bodies', async () => {
    const api = fail(new Response('<html>Bad gateway</html>', { status: 409 }));
    await expect(api.getOrder('O-10001')).rejects.toMatchObject({ kind: 'conflict', message: defaultMessage('conflict') });
  });

  it('falls back to a default message for an empty message', async () => {
    const api = fail(new Response(JSON.stringify({ message: '' }), { status: 404 }));
    await expect(api.getOrder('O-10001')).rejects.toMatchObject({ message: 'Not found.' });
  });

  it('maps a thrown TypeError to a network error', async () => {
    const fetchImpl = vi.fn<FetchLike>(async () => {
      throw new TypeError('Failed to fetch');
    });
    const api = new ApiClient({ fetchImpl, retries: 0 });
    await expect(api.listOrders()).rejects.toMatchObject({ kind: 'network', message: defaultMessage('network') });
  });
});

describe('errorMessage', () => {
  it.each([
    [new ApiError('server', 'Boom'), 'Boom'],
    [new Error('plain error'), 'plain error'],
    ['a string', 'Something went wrong.'],
  ])('errorMessage(%s)', (input, expected) => {
    expect(errorMessage(input)).toBe(expected);
  });
});
