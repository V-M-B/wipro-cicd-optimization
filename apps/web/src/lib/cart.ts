import type { CustomerTier, OrderLine, PriceQuote, Region } from '../generated/schemas';
import { applyRate, roundHalfEven, sumMoney } from './money';

/** Loyalty-tier discount applied after bulk discounts. */
export const TIER_DISCOUNT_RATES: Readonly<Record<CustomerTier, number>> = {
  STANDARD: 0,
  SILVER: 0.05,
  GOLD: 0.1,
  PLATINUM: 0.15,
};

/** Per-line bulk discount tiers, highest threshold first. */
export const BULK_TIERS: ReadonlyArray<{ minQuantity: number; rate: number }> = [
  { minQuantity: 100, rate: 0.1 },
  { minQuantity: 50, rate: 0.07 },
  { minQuantity: 10, rate: 0.03 },
];

/** Sales tax per region, applied to the discounted merchandise amount. */
export const TAX_RATES: Readonly<Record<Region, number>> = {
  NORTH: 0.08,
  SOUTH: 0.06,
  EAST: 0.0725,
  WEST: 0.0875,
};

/** Flat shipping fee per region when the free-shipping threshold is not reached. */
export const SHIPPING_RATES: Readonly<Record<Region, number>> = {
  NORTH: 7.99,
  SOUTH: 6.99,
  EAST: 5.99,
  WEST: 8.99,
};

/** Discounted merchandise amount at or above which shipping is free. */
export const FREE_SHIPPING_THRESHOLD = 100;

export type CouponKind = 'PERCENT' | 'FIXED' | 'FREE_SHIPPING';

export interface Coupon {
  code: string;
  kind: CouponKind;
  /** Rate for PERCENT (0.1 = 10%), amount for FIXED, ignored for FREE_SHIPPING. */
  value: number;
  /** Minimum eligible amount (after bulk and tier discounts). */
  minSubtotal: number;
  /** Optional cap on the discount amount for PERCENT coupons. */
  maxDiscount?: number;
  description: string;
}

export const COUPONS: Readonly<Record<string, Coupon>> = {
  SAVE10: { code: 'SAVE10', kind: 'PERCENT', value: 0.1, minSubtotal: 50, description: '10% off orders over $50' },
  WELCOME15: {
    code: 'WELCOME15',
    kind: 'PERCENT',
    value: 0.15,
    minSubtotal: 0,
    maxDiscount: 25,
    description: '15% off, up to $25',
  },
  FLAT5: { code: 'FLAT5', kind: 'FIXED', value: 5, minSubtotal: 25, description: '$5 off orders over $25' },
  BIG50: { code: 'BIG50', kind: 'FIXED', value: 50, minSubtotal: 300, description: '$50 off orders over $300' },
  FREESHIP: { code: 'FREESHIP', kind: 'FREE_SHIPPING', value: 0, minSubtotal: 0, description: 'Free shipping' },
};

export type CouponLookup =
  | { ok: true; coupon: Coupon }
  | { ok: false; reason: 'EMPTY' | 'UNKNOWN' | 'MIN_SUBTOTAL'; message: string };

export function normalizeCouponCode(code: string): string {
  return code.trim().toUpperCase();
}

/** Resolve a coupon code against the amount it would apply to. */
export function lookupCoupon(code: string | undefined, eligibleAmount: number): CouponLookup {
  const normalized = normalizeCouponCode(code ?? '');
  if (normalized === '') {
    return { ok: false, reason: 'EMPTY', message: 'No coupon code entered' };
  }
  const coupon = COUPONS[normalized];
  if (!coupon) {
    return { ok: false, reason: 'UNKNOWN', message: `Unknown coupon code "${normalized}"` };
  }
  if (eligibleAmount < coupon.minSubtotal) {
    return {
      ok: false,
      reason: 'MIN_SUBTOTAL',
      message: `${coupon.code} requires a minimum of $${coupon.minSubtotal.toFixed(2)}`,
    };
  }
  return { ok: true, coupon };
}

function assertValidLine(line: OrderLine): void {
  if (!Number.isInteger(line.quantity) || line.quantity < 1) {
    throw new RangeError(`Invalid quantity for ${line.sku}: ${line.quantity}`);
  }
  if (!Number.isFinite(line.unitPrice) || line.unitPrice < 0) {
    throw new RangeError(`Invalid unit price for ${line.sku}: ${line.unitPrice}`);
  }
}

export function lineTotal(line: OrderLine): number {
  assertValidLine(line);
  return roundHalfEven(line.quantity * line.unitPrice, 2);
}

export function cartSubtotal(lines: readonly OrderLine[]): number {
  return sumMoney(lines.map(lineTotal));
}

export function totalQuantity(lines: readonly OrderLine[]): number {
  return lines.reduce((acc, line) => acc + line.quantity, 0);
}

export function bulkDiscountRate(quantity: number): number {
  const tier = BULK_TIERS.find((t) => quantity >= t.minQuantity);
  return tier ? tier.rate : 0;
}

/** Sum of per-line bulk discounts, each rounded individually. */
export function bulkDiscount(lines: readonly OrderLine[]): number {
  return sumMoney(lines.map((line) => applyRate(lineTotal(line), bulkDiscountRate(line.quantity))));
}

export function tierDiscountRate(tier: CustomerTier): number {
  return TIER_DISCOUNT_RATES[tier];
}

export function tierDiscount(amount: number, tier: CustomerTier): number {
  return applyRate(amount, tierDiscountRate(tier));
}

/** Discount granted by a coupon on `amount`. Never exceeds the amount itself. */
export function couponDiscount(coupon: Coupon, amount: number): number {
  if (amount <= 0) return 0;
  switch (coupon.kind) {
    case 'PERCENT': {
      const raw = applyRate(amount, coupon.value);
      return coupon.maxDiscount === undefined ? raw : Math.min(raw, coupon.maxDiscount);
    }
    case 'FIXED':
      return Math.min(coupon.value, roundHalfEven(amount, 2));
    case 'FREE_SHIPPING':
      return 0;
  }
}

export function taxRate(region: Region): number {
  return TAX_RATES[region];
}

export function taxFor(amount: number, region: Region): number {
  if (amount <= 0) return 0;
  return applyRate(amount, taxRate(region));
}

export interface ShippingOptions {
  freeShipping?: boolean;
  hasItems?: boolean;
}

export function shippingFor(amount: number, region: Region, options: ShippingOptions = {}): number {
  const { freeShipping = false, hasItems = true } = options;
  if (!hasItems || freeShipping) return 0;
  if (amount >= FREE_SHIPPING_THRESHOLD) return 0;
  return SHIPPING_RATES[region];
}

/** Amount still needed to reach free shipping (0 if already reached). */
export function amountToFreeShipping(amount: number): number {
  return Math.max(0, roundHalfEven(FREE_SHIPPING_THRESHOLD - amount, 2));
}

export interface QuoteInput {
  lines: readonly OrderLine[];
  tier: CustomerTier;
  region: Region;
  couponCode?: string;
}

export interface QuoteBreakdown extends PriceQuote {
  bulkDiscount: number;
  tierDiscount: number;
  couponDiscount: number;
  coupon?: Coupon;
  couponError?: string;
}

/**
 * Price an order. Steps (each rounded to cents with banker's rounding):
 * subtotal, per-line bulk discount, tier discount, coupon, tax on the discounted amount,
 * shipping (free at/above the threshold or with FREESHIP), total.
 */
export function computeQuote(input: QuoteInput): QuoteBreakdown {
  const { lines, tier, region, couponCode } = input;
  const subtotal = cartSubtotal(lines);
  const bulk = bulkDiscount(lines);
  const afterBulk = roundHalfEven(subtotal - bulk, 2);
  const tierAmount = tierDiscount(afterBulk, tier);
  const eligible = roundHalfEven(afterBulk - tierAmount, 2);

  let coupon: Coupon | undefined;
  let couponError: string | undefined;
  let couponAmount = 0;
  if (couponCode !== undefined && normalizeCouponCode(couponCode) !== '') {
    const lookup = lookupCoupon(couponCode, eligible);
    if (lookup.ok) {
      coupon = lookup.coupon;
      couponAmount = couponDiscount(coupon, eligible);
    } else {
      couponError = lookup.message;
    }
  }

  const discount = sumMoney([bulk, tierAmount, couponAmount]);
  const taxable = roundHalfEven(subtotal - discount, 2);
  const tax = taxFor(taxable, region);
  const shipping = shippingFor(taxable, region, {
    freeShipping: coupon?.kind === 'FREE_SHIPPING',
    hasItems: lines.length > 0,
  });
  const total = sumMoney([taxable, tax, shipping]);

  const result: QuoteBreakdown = {
    subtotal,
    discount,
    tax,
    shipping,
    total,
    bulkDiscount: bulk,
    tierDiscount: tierAmount,
    couponDiscount: couponAmount,
  };
  if (coupon) result.coupon = coupon;
  if (couponError) result.couponError = couponError;
  return result;
}

/** Strip the breakdown down to the wire-format PriceQuote. */
export function toPriceQuote(breakdown: QuoteBreakdown): PriceQuote {
  const { subtotal, discount, tax, shipping, total } = breakdown;
  return { subtotal, discount, tax, shipping, total };
}
