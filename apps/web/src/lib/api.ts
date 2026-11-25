import type { Customer, Order, OrderStatus, PriceQuote, Problem, Product } from '../generated/schemas';

export type ApiErrorKind =
  | 'network'
  | 'bad_request'
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'conflict'
  | 'validation'
  | 'rate_limited'
  | 'server'
  | 'unavailable'
  | 'parse'
  | 'aborted'
  | 'unknown';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  readonly details: Record<string, string> | undefined;

  constructor(kind: ApiErrorKind, message: string, status?: number, details?: Record<string, string>) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.details = details;
  }

  get retryable(): boolean {
    return isRetryableKind(this.kind);
  }
}

export function mapStatusToKind(status: number): ApiErrorKind {
  if (status === 400) return 'bad_request';
  if (status === 401) return 'unauthorized';
  if (status === 403) return 'forbidden';
  if (status === 404) return 'not_found';
  if (status === 409) return 'conflict';
  if (status === 422) return 'validation';
  if (status === 429) return 'rate_limited';
  if (status === 502 || status === 503 || status === 504) return 'unavailable';
  if (status >= 500 && status <= 599) return 'server';
  return 'unknown';
}

export function isRetryableKind(kind: ApiErrorKind): boolean {
  return kind === 'network' || kind === 'unavailable' || kind === 'rate_limited';
}

const DEFAULT_MESSAGES: Record<ApiErrorKind, string> = {
  network: 'Could not reach the server. Check your connection.',
  bad_request: 'The request was not accepted.',
  unauthorized: 'Your session has expired. Please sign in again.',
  forbidden: 'You do not have permission to do that.',
  not_found: 'Not found.',
  conflict: 'The record was changed by someone else.',
  validation: 'Some fields are invalid.',
  rate_limited: 'Too many requests. Please slow down.',
  server: 'The server encountered an error.',
  unavailable: 'The service is temporarily unavailable.',
  parse: 'The server sent an unexpected response.',
  aborted: 'The request was cancelled.',
  unknown: 'Something went wrong.',
};

export function defaultMessage(kind: ApiErrorKind): string {
  return DEFAULT_MESSAGES[kind];
}

/** Exponential backoff: base, 2*base, 4*base ... capped at `max`. */
export function backoffDelay(attempt: number, baseMs: number, maxMs = 5_000): number {
  return Math.min(baseMs * 2 ** attempt, maxMs);
}

/** Parse a Retry-After header given in seconds. HTTP-date values are ignored. */
export function parseRetryAfter(header: string | null, maxMs = 10_000): number | undefined {
  if (header === null || !/^\d+$/.test(header.trim())) return undefined;
  return Math.min(Number(header.trim()) * 1000, maxMs);
}

export type QueryValue = string | number | boolean | undefined | null;

export function buildQuery(params: Record<string, QueryValue> = {}): string {
  const search = new URLSearchParams();
  for (const key of Object.keys(params).sort()) {
    const value = params[key];
    if (value === undefined || value === null || value === '') continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text === '' ? '' : `?${text}`;
}

export interface OrderListQuery {
  status?: OrderStatus;
  customerId?: string;
  [key: string]: QueryValue;
}

export interface CreateOrderRequest {
  customerId: string;
  lines: Array<{ sku: string; quantity: number }>;
  couponCode?: string;
}

export interface QuoteRequest {
  customerId: string;
  lines: Array<{ sku: string; quantity: number }>;
  couponCode?: string;
}

/** The surface the UI depends on. Components receive an implementation through ApiContext. */
export interface RetailApi {
  listOrders(query?: OrderListQuery, signal?: AbortSignal): Promise<Order[]>;
  getOrder(id: string, signal?: AbortSignal): Promise<Order>;
  createOrder(request: CreateOrderRequest): Promise<Order>;
  updateOrderStatus(id: string, status: OrderStatus): Promise<Order>;
  listProducts(signal?: AbortSignal): Promise<Product[]>;
  listCustomers(signal?: AbortSignal): Promise<Customer[]>;
  getCustomer(id: string, signal?: AbortSignal): Promise<Customer>;
  getQuote(request: QuoteRequest, signal?: AbortSignal): Promise<PriceQuote>;
}

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface ApiClientOptions {
  baseUrl?: string;
  fetchImpl?: FetchLike;
  /** Extra attempts after the first for idempotent (GET) requests. */
  retries?: number;
  retryDelayMs?: number;
  sleep?: (ms: number) => Promise<void>;
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

interface RequestOptions {
  body?: unknown;
  query?: Record<string, QueryValue>;
  signal?: AbortSignal | undefined;
}

const realSleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError';
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  const kind = mapStatusToKind(response.status);
  let message = defaultMessage(kind);
  let details: Record<string, string> | undefined;
  try {
    const text = await response.text();
    if (text) {
      const body = JSON.parse(text) as { [K in keyof Problem]?: unknown } & { message?: unknown; errors?: unknown };
      // orders-api answers with RFC 7807 problem details (`detail`); other services send `message`.
      const serverMessage = typeof body.detail === 'string' && body.detail !== '' ? body.detail : body.message;
      if (typeof serverMessage === 'string' && serverMessage !== '') message = serverMessage;
      if (body.errors && typeof body.errors === 'object') {
        details = Object.fromEntries(
          Object.entries(body.errors as Record<string, unknown>).map(([k, v]) => [k, String(v)]),
        );
      }
    }
  } catch {
    // Non-JSON error bodies keep the default message.
  }
  return new ApiError(kind, message, response.status, details);
}

export class ApiClient implements RetailApi {
  private readonly baseUrl: string;
  private readonly fetchImpl: FetchLike;
  private readonly retries: number;
  private readonly retryDelayMs: number;
  private readonly sleep: (ms: number) => Promise<void>;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? '').replace(/\/+$/, '');
    this.fetchImpl = options.fetchImpl ?? ((input, init) => globalThis.fetch(input, init));
    this.retries = options.retries ?? 2;
    this.retryDelayMs = options.retryDelayMs ?? 250;
    this.sleep = options.sleep ?? realSleep;
  }

  url(path: string, query?: Record<string, QueryValue>): string {
    return `${this.baseUrl}${path}${buildQuery(query)}`;
  }

  async request<T>(method: Method, path: string, options: RequestOptions = {}): Promise<T> {
    const url = this.url(path, options.query);
    const maxAttempts = method === 'GET' ? this.retries + 1 : 1;
    const headers: Record<string, string> = { Accept: 'application/json' };
    const init: RequestInit = { method, headers };
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(options.body);
    }
    if (options.signal) init.signal = options.signal;

    let lastError: ApiError = new ApiError('unknown', defaultMessage('unknown'));
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      let retryAfter: number | undefined;
      try {
        const response = await this.fetchImpl(url, init);
        if (response.ok) {
          if (response.status === 204) return undefined as T;
          const text = await response.text();
          if (text === '') return undefined as T;
          try {
            return JSON.parse(text) as T;
          } catch {
            throw new ApiError('parse', defaultMessage('parse'), response.status);
          }
        }
        lastError = await errorFromResponse(response);
        retryAfter = parseRetryAfter(response.headers.get('Retry-After'));
      } catch (error) {
        if (error instanceof ApiError) throw error;
        if (isAbortError(error)) throw new ApiError('aborted', defaultMessage('aborted'));
        lastError = new ApiError('network', defaultMessage('network'));
      }
      if (!lastError.retryable || attempt === maxAttempts - 1) break;
      await this.sleep(retryAfter ?? backoffDelay(attempt, this.retryDelayMs));
    }
    throw lastError;
  }

  listOrders(query: OrderListQuery = {}, signal?: AbortSignal): Promise<Order[]> {
    return this.request<Order[]>('GET', '/api/orders', { query, signal });
  }

  getOrder(id: string, signal?: AbortSignal): Promise<Order> {
    return this.request<Order>('GET', `/api/orders/${encodeURIComponent(id)}`, { signal });
  }

  createOrder(request: CreateOrderRequest): Promise<Order> {
    return this.request<Order>('POST', '/api/orders', { body: request });
  }

  updateOrderStatus(id: string, status: OrderStatus): Promise<Order> {
    return this.request<Order>('PATCH', `/api/orders/${encodeURIComponent(id)}`, { body: { status } });
  }

  listProducts(signal?: AbortSignal): Promise<Product[]> {
    return this.request<Product[]>('GET', '/api/products', { signal });
  }

  listCustomers(signal?: AbortSignal): Promise<Customer[]> {
    return this.request<Customer[]>('GET', '/api/customers', { signal });
  }

  getCustomer(id: string, signal?: AbortSignal): Promise<Customer> {
    return this.request<Customer>('GET', `/api/customers/${encodeURIComponent(id)}`, { signal });
  }

  getQuote(request: QuoteRequest, signal?: AbortSignal): Promise<PriceQuote> {
    return this.request<PriceQuote>('POST', '/api/quotes', { body: request, signal });
  }
}

/** Human-readable message for any thrown value. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return defaultMessage('unknown');
}
