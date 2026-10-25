import type { Customer, Order } from '../generated/schemas';
import { totalQuantity } from './cart';
import type { CustomerIndex } from './orderQuery';

export interface CsvColumn<T> {
  header: string;
  value: (row: T) => unknown;
}

export interface CsvOptions {
  delimiter?: string;
  eol?: string;
}

const FORMULA_PREFIX = /^[=+\-@\t\r]/;

/**
 * Escape a single CSV field (RFC 4180). Strings that a spreadsheet would interpret as a formula
 * are prefixed with a single quote to prevent CSV injection; numbers are left untouched.
 */
export function escapeCsvField(value: unknown, delimiter = ','): string {
  if (value === null || value === undefined) return '';
  let text: string;
  if (typeof value === 'number') {
    text = Number.isFinite(value) ? String(value) : '';
  } else if (typeof value === 'boolean') {
    text = value ? 'true' : 'false';
  } else if (value instanceof Date) {
    text = value.toISOString();
  } else {
    text = String(value);
    if (FORMULA_PREFIX.test(text)) text = `'${text}`;
  }
  if (text.includes('"') || text.includes(delimiter) || text.includes('\n') || text.includes('\r')) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function toCsv<T>(rows: readonly T[], columns: readonly CsvColumn<T>[], options: CsvOptions = {}): string {
  const { delimiter = ',', eol = '\r\n' } = options;
  const lines = [columns.map((c) => escapeCsvField(c.header, delimiter)).join(delimiter)];
  for (const row of rows) {
    lines.push(columns.map((c) => escapeCsvField(c.value(row), delimiter)).join(delimiter));
  }
  return lines.join(eol) + eol;
}

/** Parse RFC 4180 CSV into rows of fields. Handles quoted fields, escaped quotes and CRLF. */
export function parseCsv(text: string, delimiter = ','): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === delimiter) {
      row.push(field);
      field = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i += 1;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else {
      field += ch;
    }
  }
  if (field !== '' || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

export function orderCsvColumns(customers: CustomerIndex): CsvColumn<Order>[] {
  const customer = (o: Order): Customer | undefined => customers.get(o.customerId);
  return [
    { header: 'Order ID', value: (o) => o.id },
    { header: 'Created', value: (o) => o.createdAt },
    { header: 'Customer ID', value: (o) => o.customerId },
    { header: 'Customer', value: (o) => customer(o)?.name ?? '' },
    { header: 'Region', value: (o) => customer(o)?.region ?? '' },
    { header: 'Status', value: (o) => o.status },
    { header: 'Lines', value: (o) => o.lines.length },
    { header: 'Units', value: (o) => totalQuantity(o.lines) },
    { header: 'Coupon', value: (o) => o.couponCode ?? '' },
    { header: 'Total', value: (o) => o.total.toFixed(2) },
  ];
}

export function ordersToCsv(orders: readonly Order[], customers: CustomerIndex = new Map()): string {
  return toCsv(orders, orderCsvColumns(customers));
}
