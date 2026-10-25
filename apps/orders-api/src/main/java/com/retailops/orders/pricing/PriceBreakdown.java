package com.retailops.orders.pricing;

import java.math.BigDecimal;

import com.retailops.schemas.PriceQuote;

/** Full pricing result. {@link #toPriceQuote()} collapses the three discounts into one. */
public record PriceBreakdown(
        BigDecimal subtotal,
        BigDecimal bulkDiscount,
        BigDecimal tierDiscount,
        BigDecimal couponDiscount,
        BigDecimal tax,
        BigDecimal shipping,
        BigDecimal total) {

    public BigDecimal discount() {
        return Money.sum(bulkDiscount, tierDiscount, couponDiscount);
    }

    public BigDecimal netMerchandise() {
        return subtotal.subtract(discount());
    }

    public PriceQuote toPriceQuote() {
        return new PriceQuote(subtotal, discount(), tax, shipping, total);
    }
}
