import { parseIso } from './dates';
import { roundHalfEven } from './money';

export interface CurrencyOptions {
  currency?: string;
  locale?: string;
}

const currencyFormatters = new Map<string, Intl.NumberFormat>();

function currencyFormatter(locale: string, currency: string): Intl.NumberFormat {
  const key = `${locale}|${currency}`;
  let formatter = currencyFormatters.get(key);
  if (!formatter) {
    formatter = new Intl.NumberFormat(locale, { style: 'currency', currency });
    currencyFormatters.set(key, formatter);
  }
  return formatter;
}

/** Format an amount as currency. Amounts are banker's-rounded to cents first. */
export function formatCurrency(amount: number, options: CurrencyOptions = {}): string {
  const { currency = 'USD', locale = 'en-US' } = options;
  if (!Number.isFinite(amount)) return '—';
  return currencyFormatter(locale, currency).format(roundHalfEven(amount, 2));
}

/** Format a rate (0.15) as a percentage ("15%"). */
export function formatPercent(rate: number, decimals = 0): string {
  if (!Number.isFinite(rate)) return '—';
  return `${roundHalfEven(rate * 100, decimals).toFixed(decimals)}%`;
}

/** Group digits with commas: 1234567 → "1,234,567". */
export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return '—';
  const negative = value < 0;
  const [intPart, fracPart] = Math.abs(value).toString().split('.');
  const grouped = (intPart ?? '0').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${negative ? '-' : ''}${grouped}${fracPart ? `.${fracPart}` : ''}`;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${formatNumber(count)} ${count === 1 ? singular : plural}`;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "Jan 5, 2024" (UTC). Returns "Invalid date" for unparseable input. */
export function formatDate(iso: string): string {
  const date = parseIso(iso);
  if (!date) return 'Invalid date';
  return `${MONTHS[date.getUTCMonth()]} ${date.getUTCDate()}, ${date.getUTCFullYear()}`;
}

const pad2 = (n: number): string => n.toString().padStart(2, '0');

/** "2024-01-05 14:30 UTC". */
export function formatDateTime(iso: string): string {
  const date = parseIso(iso);
  if (!date) return 'Invalid date';
  return (
    `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())} ` +
    `${pad2(date.getUTCHours())}:${pad2(date.getUTCMinutes())} UTC`
  );
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Human relative time between `iso` and `now`: "just now", "5 minutes ago", "in 2 days", "yesterday". */
export function formatRelative(iso: string, now: Date): string {
  const date = parseIso(iso);
  if (!date) return 'Invalid date';
  const diff = now.getTime() - date.getTime();
  const abs = Math.abs(diff);
  const future = diff < 0;
  const phrase = (n: number, unit: string): string => {
    const text = `${n} ${unit}${n === 1 ? '' : 's'}`;
    return future ? `in ${text}` : `${text} ago`;
  };
  if (abs < 45_000) return 'just now';
  if (abs < HOUR) return phrase(Math.max(1, Math.round(abs / MINUTE)), 'minute');
  if (abs < DAY) return phrase(Math.round(abs / HOUR), 'hour');
  const days = Math.round(abs / DAY);
  if (days === 1) return future ? 'tomorrow' : 'yesterday';
  if (days < 30) return phrase(days, 'day');
  if (days < 365) return phrase(Math.round(days / 30), 'month');
  return phrase(Math.round(days / 365), 'year');
}

/** Turn an enum value like "PLATINUM" or "NORTH_EAST" into "Platinum" / "North east". */
export function humanizeEnum(value: string): string {
  const lower = value.replace(/_/g, ' ').toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}
