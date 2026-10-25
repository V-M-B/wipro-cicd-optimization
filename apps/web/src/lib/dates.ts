/** Date helpers. All calendar arithmetic is done in UTC so results do not depend on the host time zone. */

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const ISO_DATE_TIME = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:\d{2})$/;

export const MS_PER_DAY = 86_400_000;

function isValidCalendarDate(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1) return false;
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return day <= daysInMonth;
}

/**
 * Strictly parse an ISO-8601 date (`2024-01-05`) or date-time with an explicit offset
 * (`2024-01-05T10:30:00Z`). Returns null for anything else, including impossible dates.
 */
export function parseIso(value: string): Date | null {
  const dateMatch = ISO_DATE.exec(value);
  if (dateMatch) {
    const [, y, m, d] = dateMatch.map(Number) as [number, number, number, number];
    if (!isValidCalendarDate(y, m, d)) return null;
    return new Date(Date.UTC(y, m - 1, d));
  }
  const dtMatch = ISO_DATE_TIME.exec(value);
  if (dtMatch) {
    const y = Number(dtMatch[1]);
    const m = Number(dtMatch[2]);
    const d = Number(dtMatch[3]);
    const hh = Number(dtMatch[4]);
    const mm = Number(dtMatch[5]);
    const ss = Number(dtMatch[6] ?? 0);
    if (!isValidCalendarDate(y, m, d) || hh > 23 || mm > 59 || ss > 59) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  return null;
}

export function isValidIso(value: string): boolean {
  return parseIso(value) !== null;
}

/** Format a Date as `YYYY-MM-DD` (UTC). */
export function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function startOfUtcDay(date: Date): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

export function addDays(date: Date, days: number): Date {
  return new Date(date.getTime() + days * MS_PER_DAY);
}

/** Whole calendar days from `a` to `b` (UTC), negative if b is earlier. */
export function daysBetween(a: Date, b: Date): number {
  return Math.round((startOfUtcDay(b).getTime() - startOfUtcDay(a).getTime()) / MS_PER_DAY);
}

/**
 * Is the ISO timestamp within the inclusive date range `[from, to]` (both `YYYY-MM-DD`, optional)?
 * Invalid timestamps never match.
 */
export function isWithinDateRange(iso: string, from?: string, to?: string): boolean {
  const date = parseIso(iso);
  if (!date) return false;
  const day = toIsoDate(date);
  if (from && day < from) return false;
  if (to && day > to) return false;
  return true;
}

/** The `count` calendar days ending at (and including) `end`, oldest first, as `YYYY-MM-DD`. */
export function lastNDays(end: Date, count: number): string[] {
  const start = startOfUtcDay(end);
  return Array.from({ length: count }, (_, i) => toIsoDate(addDays(start, i - count + 1)));
}
