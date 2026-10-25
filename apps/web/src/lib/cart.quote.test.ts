import { describe, expect, it } from 'vitest';
import type { OrderLine } from '../generated/schemas';
import { computeQuote, toPriceQuote } from './cart';
import type { QuoteInput } from './cart';

const line = (quantity: number, unitPrice: number, sku = 'ELE-1001'): OrderLine => ({ sku, quantity, unitPrice });

describe('computeQuote scenarios (hand-calculated)', () => {
  it.each<[string, QuoteInput, { subtotal: number; discount: number; tax: number; shipping: number; total: number }]>([
    ['empty cart', { lines: [], tier: 'STANDARD', region: 'NORTH' }, { subtotal: 0, discount: 0, tax: 0, shipping: 0, total: 0 }],
    [
      'standard customer, small order pays shipping',
      { lines: [line(2, 24.99)], tier: 'STANDARD', region: 'SOUTH' },
      { subtotal: 49.98, discount: 0, tax: 3, shipping: 6.99, total: 59.97 },
    ],
    [
      'platinum tier discount',
      { lines: [line(1, 199)], tier: 'PLATINUM', region: 'WEST' },
      { subtotal: 199, discount: 29.85, tax: 14.8, shipping: 0, total: 183.95 },
    ],
    [
      'bulk then tier, discounted amount drops below free shipping',
      { lines: [line(10, 10)], tier: 'GOLD', region: 'EAST' },
      { subtotal: 100, discount: 12.7, tax: 6.33, shipping: 5.99, total: 99.62 },
    ],
    [
      'SAVE10 coupon',
      { lines: [line(3, 20)], tier: 'STANDARD', region: 'NORTH', couponCode: 'SAVE10' },
      { subtotal: 60, discount: 6, tax: 4.32, shipping: 7.99, total: 66.31 },
    ],
    [
      'WELCOME15 is capped at $25',
      { lines: [line(1, 199), line(1, 45, 'HOM-4002')], tier: 'STANDARD', region: 'SOUTH', couponCode: 'WELCOME15' },
      { subtotal: 244, discount: 25, tax: 13.14, shipping: 0, total: 232.14 },
    ],
    [
      'FLAT5 after silver discount',
      { lines: [line(2, 15)], tier: 'SILVER', region: 'NORTH', couponCode: 'FLAT5' },
      { subtotal: 30, discount: 6.5, tax: 1.88, shipping: 7.99, total: 33.37 },
    ],
    [
      'free shipping threshold uses the discounted amount',
      { lines: [line(1, 105)], tier: 'GOLD', region: 'NORTH' },
      { subtotal: 105, discount: 10.5, tax: 7.56, shipping: 7.99, total: 110.05 },
    ],
    [
      'FREESHIP removes shipping',
      { lines: [line(1, 15)], tier: 'STANDARD', region: 'WEST', couponCode: 'FREESHIP' },
      { subtotal: 15, discount: 0, tax: 1.31, shipping: 0, total: 16.31 },
    ],
    [
      'BIG50 on a large order',
      { lines: [line(2, 199)], tier: 'STANDARD', region: 'EAST', couponCode: 'BIG50' },
      { subtotal: 398, discount: 50, tax: 25.23, shipping: 0, total: 373.23 },
    ],
  ])('%s', (_name, input, expected) => {
    expect(toPriceQuote(computeQuote(input))).toEqual(expected);
  });

  it('reports a coupon below its minimum without applying it', () => {
    const quote = computeQuote({ lines: [line(2, 20)], tier: 'STANDARD', region: 'NORTH', couponCode: 'SAVE10' });
    expect(quote.couponError).toBe('SAVE10 requires a minimum of $50.00');
    expect(quote.coupon).toBeUndefined();
    expect(quote.couponDiscount).toBe(0);
    expect(quote.total).toBe(51.19);
  });

  it('reports an unknown coupon', () => {
    const quote = computeQuote({ lines: [line(1, 10)], tier: 'STANDARD', region: 'NORTH', couponCode: 'xyz' });
    expect(quote.couponError).toBe('Unknown coupon code "XYZ"');
  });

  it('accepts coupons with whitespace and lower case', () => {
    const quote = computeQuote({ lines: [line(2, 15)], tier: 'STANDARD', region: 'NORTH', couponCode: ' flat5 ' });
    expect(quote.coupon?.code).toBe('FLAT5');
    expect(quote.couponDiscount).toBe(5);
  });

  it('ignores a blank coupon', () => {
    const quote = computeQuote({ lines: [line(1, 10)], tier: 'STANDARD', region: 'NORTH', couponCode: '   ' });
    expect(quote.couponError).toBeUndefined();
    expect(quote.coupon).toBeUndefined();
  });

  it('exposes the breakdown of the discount', () => {
    const quote = computeQuote({ lines: [line(10, 10)], tier: 'GOLD', region: 'EAST' });
    expect(quote).toMatchObject({ bulkDiscount: 3, tierDiscount: 9.7, couponDiscount: 0, discount: 12.7 });
  });

  it('propagates invalid lines', () => {
    expect(() => computeQuote({ lines: [line(0, 10)], tier: 'GOLD', region: 'EAST' })).toThrow(RangeError);
  });

  it('toPriceQuote keeps only the wire fields', () => {
    const quote = computeQuote({ lines: [line(1, 10)], tier: 'GOLD', region: 'EAST', couponCode: 'FREESHIP' });
    expect(Object.keys(toPriceQuote(quote)).sort()).toEqual(['discount', 'shipping', 'subtotal', 'tax', 'total']);
  });
});
