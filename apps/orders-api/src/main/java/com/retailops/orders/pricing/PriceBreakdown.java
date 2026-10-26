package com.retailops.orders.pricing;

import java.math.BigDecimal;

import com.retailops.schemas.PriceQuote;

/**
 * Full pricing result. {@link #toPriceQuote()} collapses the three discounts into one. All amounts are in
 * {@link #CURRENCY}; the service does not support other currencies yet.
 */
public record PriceBreakdown(
        BigDecimal subtotal,
        BigDecimal bulkDiscount,
        BigDecimal tierDiscount,
        BigDecimal couponDiscount,
        BigDecimal tax,
        BigDecimal shipping,
        BigDecimal total) {

    /** ISO 4217 code of every amount the pricing service produces. */
    public static final String CURRENCY = "USD";

    public BigDecimal discount() {
        return bulkDiscount.add(tierDiscount).add(couponDiscount);
    }

    public BigDecimal netMerchandise() {
        return subtotal.subtract(discount());
    }

    public PriceQuote toPriceQuote() {
        return new PriceQuote(subtotal, discount(), tax, shipping, total, CURRENCY);
    }
}
