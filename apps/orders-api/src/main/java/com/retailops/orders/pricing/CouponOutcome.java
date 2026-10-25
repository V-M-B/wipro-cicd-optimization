package com.retailops.orders.pricing;

import java.math.BigDecimal;

public record CouponOutcome(BigDecimal discount, boolean freeShipping) {

    public static final CouponOutcome NONE = new CouponOutcome(Money.ZERO, false);
}
