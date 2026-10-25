import { describe, expect, it } from 'vitest';
import { COUPONS, couponDiscount, lookupCoupon, normalizeCouponCode } from './cart';
import type { Coupon } from './cart';

const coupon = (code: string): Coupon => {
  const found = COUPONS[code];
  if (!found) throw new Error(code);
  return found;
};

describe('normalizeCouponCode', () => {
  it.each([
    [' save10 ', 'SAVE10'],
    ['Flat5', 'FLAT5'],
    ['', ''],
  ])('%j -> %j', (input, expected) => {
    expect(normalizeCouponCode(input)).toBe(expected);
  });
});

describe('lookupCoupon', () => {
  it.each([
    ['', 100, 'EMPTY'],
    [undefined, 100, 'EMPTY'],
    ['NOPE', 100, 'UNKNOWN'],
    ['SAVE10', 49.99, 'MIN_SUBTOTAL'],
    ['BIG50', 299.99, 'MIN_SUBTOTAL'],
  ])('%j on %d fails with %s', (code, amount, reason) => {
    const result = lookupCoupon(code, amount);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe(reason);
  });

  it.each([
    ['SAVE10', 50],
    ['BIG50', 300],
    ['FLAT5', 25],
    ['WELCOME15', 0],
  ])('%s on %d is accepted', (code, amount) => {
    const result = lookupCoupon(code, amount);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.coupon.code).toBe(code.toUpperCase());
  });

  it('explains the minimum spend', () => {
    const result = lookupCoupon('SAVE10', 10);
    expect(!result.ok && result.message).toBe('SAVE10 requires a minimum of $50.00');
  });

  it('quotes the unknown code back to the user', () => {
    const result = lookupCoupon(' xyz ', 10);
    expect(!result.ok && result.message).toBe('Unknown coupon code "XYZ"');
  });
});

describe('couponDiscount', () => {
  it.each([
    ['SAVE10', 80, 8],
    ['SAVE10', 123.45, 12.34],
    ['WELCOME15', 100, 15],
    ['WELCOME15', 200, 25],
    ['FLAT5', 30, 5],
    ['FLAT5', 3, 3],
    ['BIG50', 400, 50],
    ['FREESHIP', 80, 0],
  ])('%s on %d = %d', (code, amount, expected) => {
    expect(couponDiscount(coupon(code), amount)).toBe(expected);
  });

  it('keys every coupon by its own code', () => {
    for (const [key, value] of Object.entries(COUPONS)) expect(value.code).toBe(key);
  });
});
