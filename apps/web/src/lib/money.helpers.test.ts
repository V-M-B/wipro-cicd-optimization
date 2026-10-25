import { describe, expect, it } from 'vitest';
import { allocate, applyRate, fromCents, sumMoney, toCents } from './money';

describe('toCents / fromCents', () => {
  it.each([
    [12.345, 1234],
    [12.355, 1236],
    [0.1 + 0.2, 30],
    [-4.5, -450],
    [0, 0],
  ])('toCents(%d) = %d', (amount, cents) => {
    expect(toCents(amount)).toBe(cents);
  });

  it.each([
    [1234, 12.34],
    [0, 0],
  ])('fromCents(%d) = %d', (cents, amount) => {
    expect(fromCents(cents)).toBe(amount);
  });

  it('rejects fractional cents', () => {
    expect(() => fromCents(1.5)).toThrow(RangeError);
  });
});

describe('sumMoney', () => {
  it.each([
    [[0.1, 0.2], 0.3],
    [[], 0],
    [[19.99, 5.01], 25],
    [[19.99, 5.01, 0.005], 25],
  ])('sumMoney(%j) = %d', (amounts, expected) => {
    expect(sumMoney(amounts)).toBe(expected);
  });
});

describe('applyRate', () => {
  it.each([
    [100, 0.0725, 7.25],
    [10.1, 0.05, 0.5],
    [10.3, 0.05, 0.52],
    [19.99, 0.0875, 1.75],
  ])('applyRate(%d, %d) = %d', (amount, rate, expected) => {
    expect(applyRate(amount, rate)).toBe(expected);
  });
});

describe('allocate', () => {
  it.each([
    [100, 3, [33.34, 33.33, 33.33]],
    [0.05, 3, [0.02, 0.02, 0.01]],
    [10, 4, [2.5, 2.5, 2.5, 2.5]],
    [-10, 3, [-3.34, -3.33, -3.33]],
    [7, 1, [7]],
  ])('allocate(%d, %d) = %j', (amount, parts, expected) => {
    const shares = allocate(amount, parts);
    expect(shares).toEqual(expected);
    expect(sumMoney(shares)).toBe(amount);
  });

  it.each([0, -1, 2.5])('rejects %d parts', (parts) => {
    expect(() => allocate(5, parts)).toThrow(RangeError);
  });
});
