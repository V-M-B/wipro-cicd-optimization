import { describe, expect, it } from 'vitest';
import { addDays, daysBetween, isValidIso, isWithinDateRange, lastNDays, parseIso, startOfUtcDay, toIsoDate } from './dates';

describe('parseIso', () => {
  it.each([
    ['2024-01-05', '2024-01-05T00:00:00.000Z'],
    ['2024-02-29', '2024-02-29T00:00:00.000Z'],
    ['2024-01-05T10:30Z', '2024-01-05T10:30:00.000Z'],
    ['2024-01-05T10:30:15.250Z', '2024-01-05T10:30:15.250Z'],
    ['2024-01-05T10:30:00+02:00', '2024-01-05T08:30:00.000Z'],
  ])('parses %s', (input, expected) => {
    expect(parseIso(input)?.toISOString()).toBe(expected);
  });

  it.each([
    '',
    '2024-1-5',
    '2023-02-29',
    '2024-04-31',
    '2024-01-05T24:00:00Z',
    '2024-01-05T10:30:00',
  ])('rejects %j', (input) => {
    expect(parseIso(input)).toBeNull();
    expect(isValidIso(input)).toBe(false);
  });
});

describe('calendar helpers', () => {
  it('formats a date as YYYY-MM-DD in UTC', () => {
    expect(toIsoDate(new Date('2024-03-01T23:59:59Z'))).toBe('2024-03-01');
  });

  it('truncates to the start of the UTC day', () => {
    expect(startOfUtcDay(new Date('2024-03-01T18:45:00Z')).toISOString()).toBe('2024-03-01T00:00:00.000Z');
  });

  it.each([
    ['2024-02-28', 1, '2024-02-29'],
    ['2024-02-28', 2, '2024-03-01'],
    ['2024-01-01', -1, '2023-12-31'],
  ])('addDays(%s, %d) = %s', (start, days, expected) => {
    expect(toIsoDate(addDays(new Date(start), days))).toBe(expected);
  });

  it.each([
    ['2024-03-01T23:00:00Z', '2024-03-02T01:00:00Z', 1],
    ['2024-01-01', '2024-12-31', 365],
    ['2024-03-10', '2024-03-01', -9],
    ['2024-03-10T00:00:00Z', '2024-03-10T23:59:59Z', 0],
  ])('daysBetween(%s, %s) = %d', (a, b, expected) => {
    expect(daysBetween(new Date(a), new Date(b))).toBe(expected);
  });
});

describe('isWithinDateRange', () => {
  it.each([
    ['2024-03-05T10:00:00Z', '2024-03-01', '2024-03-31', true],
    ['2024-03-01T00:00:00Z', '2024-03-01', '2024-03-31', true],
    ['2024-04-01T00:00:00Z', '2024-03-01', '2024-03-31', false],
    ['2024-02-29T23:59:59Z', '2024-03-01', undefined, false],
    ['2030-01-01T00:00:00Z', '2024-03-01', undefined, true],
    ['not-a-date', undefined, undefined, false],
  ])('%s in [%s, %s] -> %s', (iso, from, to, expected) => {
    expect(isWithinDateRange(iso, from, to)).toBe(expected);
  });
});

describe('lastNDays', () => {
  it('lists the trailing window oldest first', () => {
    expect(lastNDays(new Date('2024-03-02T15:00:00Z'), 4)).toEqual(['2024-02-28', '2024-02-29', '2024-03-01', '2024-03-02']);
  });

  it('returns an empty list for zero days', () => {
    expect(lastNDays(new Date('2024-03-02T15:00:00Z'), 0)).toEqual([]);
  });
});
