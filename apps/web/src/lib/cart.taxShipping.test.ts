import { describe, expect, it } from 'vitest';
import { RegionValues } from '../generated/schemas';
import { SHIPPING_RATES, TAX_RATES, amountToFreeShipping, shippingFor, taxFor, taxRate } from './cart';

describe('taxFor', () => {
  it.each([
    ['NORTH', 100, 8],
    ['SOUTH', 100, 6],
    ['EAST', 100, 7.25],
    ['WEST', 100, 8.75],
    ['EAST', 19.99, 1.45],
    ['SOUTH', 10.1, 0.61],
    ['WEST', 0, 0],
    ['NORTH', -5, 0],
  ] as const)('%s on %d = %d', (region, amount, expected) => {
    expect(taxFor(amount, region)).toBe(expected);
  });

  it('covers every region in the schema', () => {
    for (const region of RegionValues) {
      expect(TAX_RATES[region]).toBeGreaterThan(0);
      expect(taxRate(region)).toBe(TAX_RATES[region]);
    }
  });
});

describe('shippingFor', () => {
  it.each([
    [50, 'NORTH', {}, 7.99],
    [99.99, 'SOUTH', {}, 6.99],
    [0.01, 'EAST', {}, 5.99],
    [80, 'WEST', {}, 8.99],
    [100, 'EAST', {}, 0],
    [150, 'WEST', {}, 0],
    [20, 'NORTH', { freeShipping: true }, 0],
    [0, 'WEST', { hasItems: false }, 0],
  ] as const)('%d to %s with %j costs %d', (amount, region, options, expected) => {
    expect(shippingFor(amount, region, options)).toBe(expected);
  });

  it('has a rate for every region', () => {
    expect(Object.keys(SHIPPING_RATES).sort()).toEqual([...RegionValues].sort());
  });
});

describe('amountToFreeShipping', () => {
  it.each([
    [0, 100],
    [60, 40],
    [99.99, 0.01],
    [100, 0],
    [150, 0],
  ])('from %d needs %d more', (amount, expected) => {
    expect(amountToFreeShipping(amount)).toBe(expected);
  });
});
