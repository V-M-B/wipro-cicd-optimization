import { describe, expect, it } from 'vitest';
import { formatCurrency, formatNumber, formatPercent } from './format';

const NBSP = String.fromCharCode(0xa0);

describe('formatCurrency', () => {
  it.each([
    [1234.5, '$1,234.50'],
    [0, '$0.00'],
    [-5, '-$5.00'],
    [0.005, '$0.00'],
    [0.015, '$0.02'],
    [1_000_000, '$1,000,000.00'],
    [19.999, '$20.00'],
  ])('formats %d as %s', (amount, expected) => {
    expect(formatCurrency(amount)).toBe(expected);
  });

  it.each([NaN, Infinity])('renders %d as an em dash', (amount) => {
    expect(formatCurrency(amount)).toBe('—');
  });

  it('supports other currencies and locales', () => {
    expect(formatCurrency(1234.5, { currency: 'GBP', locale: 'en-GB' })).toBe('£1,234.50');
    expect(formatCurrency(1234.5, { currency: 'EUR', locale: 'de-DE' })).toBe(`1.234,50${NBSP}€`);
  });
});

describe('formatPercent', () => {
  it.each([
    [0.15, 0, '15%'],
    [0.1234, 1, '12.3%'],
    [0, 0, '0%'],
    [1, 0, '100%'],
    [0.125, 0, '12%'],
    [0.135, 0, '14%'],
    [0.5, 2, '50.00%'],
  ])('formatPercent(%d, %d) = %s', (rate, decimals, expected) => {
    expect(formatPercent(rate, decimals)).toBe(expected);
  });

  it('handles non-finite input', () => {
    expect(formatPercent(NaN)).toBe('—');
  });
});

describe('formatNumber', () => {
  it.each([
    [0, '0'],
    [999, '999'],
    [1000, '1,000'],
    [1234567, '1,234,567'],
    [-1234.5, '-1,234.5'],
  ])('formatNumber(%d) = %s', (value, expected) => {
    expect(formatNumber(value)).toBe(expected);
  });
});
