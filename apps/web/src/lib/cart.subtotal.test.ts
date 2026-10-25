import { describe, expect, it } from 'vitest';
import { cartSubtotal, lineTotal, totalQuantity } from './cart';

describe('lineTotal', () => {
  it.each([
    [3, 19.99, 59.97],
    [1, 0, 0],
    [7, 0.1, 0.7],
    [3, 0.335, 1],
    [12, 8.25, 99],
    [999, 199, 198801],
  ])('%d x %d = %d', (quantity, unitPrice, expected) => {
    expect(lineTotal({ sku: 'ELE-1001', quantity, unitPrice })).toBe(expected);
  });

  it.each([0, -1, 1.5, NaN])('rejects quantity %d', (quantity) => {
    expect(() => lineTotal({ sku: 'ELE-1001', quantity, unitPrice: 1 })).toThrow(/Invalid quantity for ELE-1001/);
  });

  it.each([-0.01, NaN, Infinity])('rejects unit price %d', (unitPrice) => {
    expect(() => lineTotal({ sku: 'ELE-1001', quantity: 1, unitPrice })).toThrow(/Invalid unit price/);
  });
});

describe('cartSubtotal', () => {
  it('is zero for an empty cart', () => {
    expect(cartSubtotal([])).toBe(0);
  });

  it('adds line totals exactly', () => {
    expect(
      cartSubtotal([
        { sku: 'ELE-1001', quantity: 2, unitPrice: 24.99 },
        { sku: 'ELE-1002', quantity: 1, unitPrice: 39.5 },
      ]),
    ).toBe(89.48);
  });

  it('avoids floating point drift', () => {
    expect(
      cartSubtotal([
        { sku: 'GRO-2001', quantity: 3, unitPrice: 0.1 },
        { sku: 'GRO-2002', quantity: 3, unitPrice: 0.2 },
      ]),
    ).toBe(0.9);
  });
});

describe('totalQuantity', () => {
  it.each([
    [[], 0],
    [[1], 1],
    [[2, 3, 5], 10],
  ])('sums %j to %d', (quantities, expected) => {
    expect(totalQuantity(quantities.map((quantity) => ({ sku: 'TOY-5001', quantity, unitPrice: 1 })))).toBe(expected);
  });
});
