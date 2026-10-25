package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Objects;

/**
 * A coupon rule. {@code minSpend}, {@code maxDiscount}, {@code validFrom} and {@code expiresOn} are
 * optional (null = no constraint). Validity dates are inclusive.
 */
public record Coupon(
        String code,
        CouponType type,
        BigDecimal value,
        BigDecimal minSpend,
        BigDecimal maxDiscount,
        LocalDate validFrom,
        LocalDate expiresOn,
        boolean active) {

    public Coupon {
        Objects.requireNonNull(code, "code");
        Objects.requireNonNull(type, "type");
        value = value == null ? BigDecimal.ZERO : value;
        if (value.signum() < 0) {
            throw new IllegalArgumentException("coupon value must not be negative");
        }
        if (type == CouponType.PERCENTAGE && value.compareTo(new BigDecimal("100")) > 0) {
            throw new IllegalArgumentException("percentage coupon cannot exceed 100%");
        }
        if (validFrom != null && expiresOn != null && expiresOn.isBefore(validFrom)) {
            throw new IllegalArgumentException("coupon expires before it becomes valid");
        }
    }

    public static Coupon percentage(String code, String percent) {
        return new Coupon(code, CouponType.PERCENTAGE, new BigDecimal(percent), null, null, null, null, true);
    }

    public static Coupon fixed(String code, String amount) {
        return new Coupon(code, CouponType.FIXED_AMOUNT, new BigDecimal(amount), null, null, null, null, true);
    }

    public static Coupon freeShipping(String code) {
        return new Coupon(code, CouponType.FREE_SHIPPING, BigDecimal.ZERO, null, null, null, null, true);
    }

    public Coupon withMinSpend(String amount) {
        return new Coupon(code, type, value, new BigDecimal(amount), maxDiscount, validFrom, expiresOn, active);
    }

    public Coupon withMaxDiscount(String amount) {
        return new Coupon(code, type, value, minSpend, new BigDecimal(amount), validFrom, expiresOn, active);
    }

    public Coupon withValidity(LocalDate from, LocalDate until) {
        return new Coupon(code, type, value, minSpend, maxDiscount, from, until, active);
    }

    public Coupon inactive() {
        return new Coupon(code, type, value, minSpend, maxDiscount, validFrom, expiresOn, false);
    }
}
