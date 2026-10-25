package com.retailops.orders.pricing;

public enum CouponType {
    /** {@code value} is a percentage (e.g. 10 = 10%), optionally capped by {@code maxDiscount}. */
    PERCENTAGE,
    /** {@code value} is a fixed amount, never more than the discountable amount. */
    FIXED_AMOUNT,
    /** Waives shipping; {@code value} is ignored. */
    FREE_SHIPPING
}
