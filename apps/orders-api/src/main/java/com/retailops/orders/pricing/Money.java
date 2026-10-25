package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Objects;

/** Monetary arithmetic helpers. All amounts are rounded HALF_EVEN to 2 decimal places. */
public final class Money {

    public static final int SCALE = 2;
    public static final RoundingMode ROUNDING = RoundingMode.HALF_EVEN;
    public static final BigDecimal ZERO = BigDecimal.ZERO.setScale(SCALE);

    private Money() {
    }

    public static BigDecimal round(BigDecimal amount) {
        Objects.requireNonNull(amount, "amount");
        return amount.setScale(SCALE, ROUNDING);
    }

    public static BigDecimal of(String amount) {
        return round(new BigDecimal(amount));
    }

    /** {@code round(amount * rate)} where rate is a fraction, e.g. 0.05 for 5%. */
    public static BigDecimal percentOf(BigDecimal amount, BigDecimal rate) {
        Objects.requireNonNull(rate, "rate");
        return round(Objects.requireNonNull(amount, "amount").multiply(rate));
    }

    public static BigDecimal min(BigDecimal a, BigDecimal b) {
        return a.compareTo(b) <= 0 ? a : b;
    }

    public static BigDecimal max(BigDecimal a, BigDecimal b) {
        return a.compareTo(b) >= 0 ? a : b;
    }

    public static boolean isNegative(BigDecimal amount) {
        return amount.signum() < 0;
    }
}
