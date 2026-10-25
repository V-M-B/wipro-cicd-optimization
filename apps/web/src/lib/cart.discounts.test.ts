import { describe, expect, it } from 'vitest';
import { CustomerTierValues } from '../generated/schemas';
import { BULK_TIERS, TIER_DISCOUNT_RATES, bulkDiscount, bulkDiscountRate, tierDiscount, tierDiscountRate } from './cart';

describe('bulkDiscountRate', () => {
  it.each([
    [0, 0],
    [1, 0],
    [9, 0],
    [10, 0.03],
    [49, 0.03],
    [50, 0.07],
    [99, 0.07],
    [100, 0.1],
  ])('quantity %d -> %d', (quantity, rate) => {
    expect(bulkDiscountRate(quantity)).toBe(rate);
  });

  it('lists tiers from the highest threshold down', () => {
    const thresholds = BULK_TIERS.map((t) => t.minQuantity);
    expect(thresholds).toEqual([...thresholds].sort((a, b) => b - a));
  });
});

describe('bulkDiscount', () => {
  it.each([
    ['no bulk lines', [{ quantity: 9, unitPrice: 10 }], 0],
    ['3% tier', [{ quantity: 10, unitPrice: 10 }], 3],
    ['7% tier', [{ quantity: 50, unitPrice: 2 }], 7],
    ['10% tier', [{ quantity: 100, unitPrice: 1.99 }], 19.9],
    [
      'only qualifying lines',
      [
        { quantity: 9, unitPrice: 10 },
        { quantity: 10, unitPrice: 10 },
      ],
      3,
    ],
    [
      'per-line rounding (0.045 -> 0.04 twice, not 0.09 pooled)',
      [
        { quantity: 10, unitPrice: 0.15 },
        { quantity: 10, unitPrice: 0.15 },
      ],
      0.08,
    ],
  ])('%s', (_name, lines, expected) => {
    expect(bulkDiscount(lines.map((l, i) => ({ sku: `GRO-200${i}`, ...l })))).toBe(expected);
  });
});

describe('tier discounts', () => {
  it.each([
    ['STANDARD', 0],
    ['SILVER', 0.05],
    ['GOLD', 0.1],
    ['PLATINUM', 0.15],
  ] as const)('%s rate is %d', (tier, rate) => {
    expect(tierDiscountRate(tier)).toBe(rate);
  });

  it('defines a rate for every tier in the schema', () => {
    expect(Object.keys(TIER_DISCOUNT_RATES).sort()).toEqual([...CustomerTierValues].sort());
  });

  it.each([
    [200, 'SILVER', 10],
    [200, 'GOLD', 20],
    [200, 'PLATINUM', 30],
    [33.33, 'SILVER', 1.67],
    [10.1, 'SILVER', 0.5],
    [10.3, 'SILVER', 0.52],
  ] as const)('tierDiscount(%d, %s) = %d', (amount, tier, expected) => {
    expect(tierDiscount(amount, tier)).toBe(expected);
  });
});
