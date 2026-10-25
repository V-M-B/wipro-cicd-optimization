package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Objects;

import org.springframework.stereotype.Component;

/**
 * Applies a coupon. Eligibility (active, validity window, minimum spend against the merchandise
 * subtotal) is checked first; the discount is computed on the amount left after bulk and tier
 * discounts and never exceeds it.
 */
@Component
public class CouponEvaluator {

    public void checkEligibility(Coupon coupon, BigDecimal merchandiseSubtotal, LocalDate date) {
        Objects.requireNonNull(coupon, "coupon");
        Objects.requireNonNull(date, "date");
        if (!coupon.active()) {
            throw new CouponRejectedException(coupon.code(), CouponRejectionReason.INACTIVE);
        }
        if (coupon.validFrom() != null && date.isBefore(coupon.validFrom())) {
            throw new CouponRejectedException(coupon.code(), CouponRejectionReason.NOT_YET_VALID);
        }
        if (coupon.expiresOn() != null && date.isAfter(coupon.expiresOn())) {
            throw new CouponRejectedException(coupon.code(), CouponRejectionReason.EXPIRED);
        }
        if (coupon.minSpend() != null && merchandiseSubtotal.compareTo(coupon.minSpend()) < 0) {
            throw new CouponRejectedException(coupon.code(), CouponRejectionReason.MIN_SPEND_NOT_MET);
        }
    }

    public CouponOutcome evaluate(Coupon coupon, BigDecimal merchandiseSubtotal, BigDecimal discountBase,
            LocalDate date) {
        checkEligibility(coupon, merchandiseSubtotal, date);
        return switch (coupon.type()) {
            case PERCENTAGE -> {
                BigDecimal discount = Money.percentOf(discountBase, coupon.value().movePointLeft(2));
                if (coupon.maxDiscount() != null) {
                    discount = Money.min(discount, Money.round(coupon.maxDiscount()));
                }
                yield new CouponOutcome(Money.min(discount, discountBase), false);
            }
            case FIXED_AMOUNT -> new CouponOutcome(Money.min(Money.round(coupon.value()), discountBase), false);
            case FREE_SHIPPING -> new CouponOutcome(Money.ZERO, true);
        };
    }
}
