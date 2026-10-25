import { describe, expect, it } from 'vitest';
import { formatDate, formatDateTime, formatRelative, humanizeEnum, pluralize } from './format';

describe('formatDate', () => {
  it.each([
    ['2024-01-05', 'Jan 5, 2024'],
    ['2024-12-31T23:59:59Z', 'Dec 31, 2024'],
    ['2024-03-01T00:30:00+05:30', 'Feb 29, 2024'],
    ['2024-02-30', 'Invalid date'],
  ])('formatDate(%s) = %s', (iso, expected) => {
    expect(formatDate(iso)).toBe(expected);
  });
});

describe('formatDateTime', () => {
  it.each([
    ['2024-01-05T14:30:00Z', '2024-01-05 14:30 UTC'],
    ['2024-01-05T14:30:00-02:00', '2024-01-05 16:30 UTC'],
    ['2024-01-05', '2024-01-05 00:00 UTC'],
    ['2024-01-05T09:05:59.999Z', '2024-01-05 09:05 UTC'],
    ['2024-13-01T00:00:00Z', 'Invalid date'],
  ])('formatDateTime(%s) = %s', (iso, expected) => {
    expect(formatDateTime(iso)).toBe(expected);
  });
});

describe('formatRelative', () => {
  const now = new Date('2024-03-10T12:00:00Z');

  it.each([
    ['2024-03-10T12:00:00Z', 'just now'],
    ['2024-03-10T11:59:15Z', '1 minute ago'],
    ['2024-03-10T11:55:00Z', '5 minutes ago'],
    ['2024-03-10T09:00:00Z', '3 hours ago'],
    ['2024-03-09T12:00:00Z', 'yesterday'],
    ['2024-03-07T12:00:00Z', '3 days ago'],
    ['2023-03-10T12:00:00Z', '1 year ago'],
    ['2024-03-10T12:05:00Z', 'in 5 minutes'],
    ['2024-03-11T12:00:00Z', 'tomorrow'],
    ['not a date', 'Invalid date'],
  ])('%s relative to now is %s', (iso, expected) => {
    expect(formatRelative(iso, now)).toBe(expected);
  });
});

describe('pluralize', () => {
  it.each([
    [1, 'order', undefined, '1 order'],
    [0, 'order', undefined, '0 orders'],
    [2, 'box', 'boxes', '2 boxes'],
    [1500, 'unit', undefined, '1,500 units'],
  ])('pluralize(%d, %s)', (count, singular, plural, expected) => {
    expect(pluralize(count, singular, plural)).toBe(expected);
  });
});

describe('humanizeEnum', () => {
  it.each([
    ['PLATINUM', 'Platinum'],
    ['NORTH_EAST', 'North east'],
  ])('%s -> %s', (value, expected) => {
    expect(humanizeEnum(value)).toBe(expected);
  });
});
