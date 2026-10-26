import { describe, expect, it } from 'vitest';
import { customers, orders } from '../test/fixtures';
import { escapeCsvField, needsQuoting, ordersToCsv, parseCsv, toCsv } from './csv';
import { indexCustomers } from './orderQuery';

describe('escapeCsvField', () => {
  it.each([
    ['plain', 'plain'],
    ['a,b', '"a,b"'],
    ['say "hi"', '"say ""hi"""'],
    ['line\nbreak', '"line\nbreak"'],
    ['cr\rhere', '"cr\rhere"'],
    ['=SUM(A1:A2)', "'=SUM(A1:A2)"],
    ['+1', "'+1"],
    ['-cmd', "'-cmd"],
    ['@foo', "'@foo"],
    [-12.5, '-12.5'],
    [0, '0'],
    [NaN, ''],
    [true, 'true'],
    [null, ''],
    [undefined, ''],
    [new Date('2024-03-01T09:00:00Z'), '2024-03-01T09:00:00.000Z'],
  ])('escapeCsvField(%j) = %j', (value, expected) => {
    expect(escapeCsvField(value)).toBe(expected);
  });

  it('quotes fields containing a custom delimiter', () => {
    expect(escapeCsvField('a;b', ';')).toBe('"a;b"');
    expect(escapeCsvField('a,b', ';')).toBe('a,b');
  });

  it('quotes formula-like strings that also contain the delimiter', () => {
    expect(escapeCsvField('=1,2')).toBe(`"'=1,2"`);
  });
});

describe('needsQuoting', () => {
  it.each([
    ['plain', ',', false],
    ['', ',', false],
    ['a,b', ',', true],
    ['a,b', '\t', false],
    ['a\tb', '\t', true],
    ['"', ',', true],
    ['x\r\ny', ',', true],
  ])('needsQuoting(%j, %j) = %s', (text, delimiter, expected) => {
    expect(needsQuoting(text, delimiter)).toBe(expected);
  });
});

describe('toCsv / parseCsv', () => {
  const rows = [
    { name: 'Asha, R.', note: 'said "ok"' },
    { name: 'Ben', note: 'multi\nline' },
  ];
  const columns = [
    { header: 'Name', value: (r: (typeof rows)[number]) => r.name },
    { header: 'Note', value: (r: (typeof rows)[number]) => r.note },
  ];

  it('writes a header row and CRLF line endings', () => {
    expect(toCsv(rows, columns)).toBe('Name,Note\r\n"Asha, R.","said ""ok"""\r\nBen,"multi\nline"\r\n');
  });

  it('supports other delimiters and line endings', () => {
    expect(toCsv([{ name: 'x', note: 'y' }], columns, { delimiter: '\t', eol: '\n' })).toBe('Name\tNote\nx\ty\n');
  });

  it('round-trips through parseCsv', () => {
    expect(parseCsv(toCsv(rows, columns))).toEqual([
      ['Name', 'Note'],
      ['Asha, R.', 'said "ok"'],
      ['Ben', 'multi\nline'],
    ]);
  });

  it.each([
    ['a,b\nc,d', [['a', 'b'], ['c', 'd']]],
    ['a,,c', [['a', '', 'c']]],
    ['"x""y",z', [['x"y', 'z']]],
    ['', []],
    ['only', [['only']]],
  ])('parseCsv(%j)', (text, expected) => {
    expect(parseCsv(text)).toEqual(expected);
  });
});

describe('ordersToCsv', () => {
  const csv = ordersToCsv(orders, indexCustomers(customers));
  const parsed = parseCsv(csv);

  it('has one row per order plus a header', () => {
    expect(parsed).toHaveLength(orders.length + 1);
    expect(parsed[0]).toEqual(['Order ID', 'Created', 'Customer ID', 'Customer', 'Region', 'Status', 'Lines', 'Units', 'Coupon', 'Total']);
  });

  it('includes customer details and fixed-point totals', () => {
    const first = orders[0];
    expect(parsed[1]).toEqual([
      first?.id,
      first?.createdAt,
      'C-0001',
      'Asha Rao',
      'NORTH',
      first?.status,
      String(first?.lines.length),
      String(first?.lines.reduce((a, l) => a + l.quantity, 0)),
      '',
      first?.total.toFixed(2),
    ]);
  });

  it('leaves customer columns blank when the customer is unknown', () => {
    const row = parseCsv(ordersToCsv(orders.slice(0, 1)))[1];
    expect(row?.[3]).toBe('');
    expect(row?.[4]).toBe('');
  });
});
