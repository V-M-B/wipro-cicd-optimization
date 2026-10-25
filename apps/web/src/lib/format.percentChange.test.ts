import { describe, expect, it } from 'vitest';
import { formatPercentChange } from './format';

describe('formatPercentChange', () => {
  it.each([
    [120, 100, '+20.0%'],
    [75, 100, '-25.0%'],
    [100, 100, '0.0%'],
    [250, 100, '+150.0%'],
    [0, 80, '-100.0%'],
    [-50, -100, '+50.0%'],
  ])('formatPercentChange(%d, %d) = %s', (current, previous, expected) => {
    expect(formatPercentChange(current, previous)).toBe(expected);
  });

  it('respects the requested number of decimals', () => {
    expect(formatPercentChange(1, 3, 0)).toBe('-67%');
    expect(formatPercentChange(101.234, 100, 2)).toBe('+1.23%');
  });

  it('does not attach a sign to changes that round to zero', () => {
    expect(formatPercentChange(100.04, 100)).toBe('0.0%');
    expect(formatPercentChange(99.96, 100)).toBe('0.0%');
  });

  it.each([
    [10, 0],
    [NaN, 10],
    [10, Infinity],
  ])('has no baseline for (%d, %d)', (current, previous) => {
    expect(formatPercentChange(current, previous)).toBe('—');
  });
});
