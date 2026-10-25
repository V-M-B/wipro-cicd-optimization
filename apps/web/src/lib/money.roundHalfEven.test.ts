import { describe, expect, it } from 'vitest';
import { roundHalfEven } from './money';

describe('roundHalfEven', () => {
  it.each([
    [0.125, 2, 0.12],
    [0.135, 2, 0.14],
    [2.675, 2, 2.68],
    [1.005, 2, 1],
    [1.025, 2, 1.02],
    [99.995, 2, 100],
    [10.4449, 2, 10.44],
    [-1.005, 2, -1],
    [0.5, 0, 0],
    [1.5, 0, 2],
    [2.5, 0, 2],
    [-2.5, 0, -2],
    [1.0005, 3, 1],
    [1.0015, 3, 1.002],
    [0, 2, 0],
  ])('roundHalfEven(%d, %d) = %d', (value, decimals, expected) => {
    expect(roundHalfEven(value, decimals)).toBe(expected);
  });

  it('defaults to two decimals', () => {
    expect(roundHalfEven(7.125)).toBe(7.12);
  });

  it('never returns negative zero', () => {
    expect(Object.is(roundHalfEven(-0.001), 0)).toBe(true);
    expect(Object.is(roundHalfEven(-0), 0)).toBe(true);
  });

  it.each([NaN, Infinity, -Infinity])('rejects non-finite value %d', (value) => {
    expect(() => roundHalfEven(value)).toThrow(RangeError);
  });

  it.each([-1, 1.5, 11])('rejects unsupported decimals %d', (decimals) => {
    expect(() => roundHalfEven(1, decimals)).toThrow(/decimals/);
  });
});
