package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import com.retailops.orders.support.TestFixtures;

class CouponEvaluatorTest {

    private static final LocalDate TODAY = TestFixtures.PRICING_DATE;

    private final CouponEvaluator evaluator = new CouponEvaluator();

    private CouponOutcome apply(Coupon coupon, String subtotal, String base) {
        return evaluator.evaluate(coupon, new BigDecimal(subtotal), new BigDecimal(base), TODAY);
    }

    @Test
    void percentageDiscountOnDiscountBase() {
        assertThat(apply(Coupon.percentage("P10", "10"), "100.00", "80.00").discount())
                .isEqualTo(new BigDecimal("8.00"));
    }

    @Test
    void percentageIsCappedByMaxDiscount() {
        assertThat(apply(Coupon.percentage("P10", "10").withMaxDiscount("50"), "800.00", "800.00").discount())
                .isEqualTo(new BigDecimal("50.00"));
    }

    @Test
    void percentageRoundsHalfEven() {
        assertThat(apply(Coupon.percentage("P10", "10"), "0.25", "0.25").discount())
                .isEqualTo(new BigDecimal("0.02"));
    }

    @Test
    void hundredPercentEqualsBase() {
        assertThat(apply(Coupon.percentage("ALL", "100"), "42.42", "42.42").discount())
                .isEqualTo(new BigDecimal("42.42"));
    }

    @Test
    void fixedAmountDiscount() {
        CouponOutcome outcome = apply(Coupon.fixed("F5", "5"), "80.00", "80.00");
        assertThat(outcome.discount()).isEqualTo(new BigDecimal("5.00"));
        assertThat(outcome.freeShipping()).isFalse();
    }

    @Test
    void fixedAmountNeverExceedsBase() {
        assertThat(apply(Coupon.fixed("F15", "15"), "10.00", "10.00").discount())
                .isEqualTo(new BigDecimal("10.00"));
    }

    @Test
    void freeShippingCouponHasNoMonetaryDiscount() {
        CouponOutcome outcome = apply(Coupon.freeShipping("SHIP"), "20.00", "20.00");
        assertThat(outcome.discount()).isEqualTo(Money.ZERO);
        assertThat(outcome.freeShipping()).isTrue();
    }

    @Test
    void minSpendMetExactly() {
        assertThat(apply(Coupon.fixed("F5", "5").withMinSpend("25.00"), "25.00", "25.00").discount())
                .isEqualTo(new BigDecimal("5.00"));
    }

    @Test
    void minSpendIsCheckedAgainstSubtotalNotDiscountedBase() {
        assertThat(apply(Coupon.fixed("F5", "5").withMinSpend("28.00"), "30.00", "25.00").discount())
                .isEqualTo(new BigDecimal("5.00"));
    }

    @Test
    void validOnFirstAndLastDayInclusive() {
        Coupon oneDay = Coupon.fixed("DAY", "1").withValidity(TODAY, TODAY);
        assertThat(apply(oneDay, "10.00", "10.00").discount()).isEqualTo(new BigDecimal("1.00"));
    }

    static Stream<Arguments> rejectedCoupons() {
        return Stream.of(
                Arguments.of(Coupon.percentage("OFF", "10").inactive(), "100.00", CouponRejectionReason.INACTIVE),
                Arguments.of(Coupon.percentage("SOON", "10").withValidity(TODAY.plusDays(1), null), "100.00",
                        CouponRejectionReason.NOT_YET_VALID),
                Arguments.of(Coupon.percentage("OLD", "10").withValidity(null, TODAY.minusDays(1)), "100.00",
                        CouponRejectionReason.EXPIRED),
                Arguments.of(Coupon.fixed("MIN", "5").withMinSpend("25.00"), "24.99",
                        CouponRejectionReason.MIN_SPEND_NOT_MET),
                Arguments.of(Coupon.percentage("BOTH", "10").withValidity(null, TODAY.minusDays(1)).inactive(),
                        "100.00", CouponRejectionReason.INACTIVE),
                Arguments.of(Coupon.freeShipping("SHIPMIN").withMinSpend("30.00"), "29.99",
                        CouponRejectionReason.MIN_SPEND_NOT_MET));
    }

    @ParameterizedTest(name = "{0} -> {2}")
    @MethodSource("rejectedCoupons")
    void ineligibleCouponsAreRejectedWithReason(Coupon coupon, String subtotal, CouponRejectionReason reason) {
        assertThatThrownBy(() -> apply(coupon, subtotal, subtotal))
                .isInstanceOfSatisfying(CouponRejectedException.class, ex -> {
                    assertThat(ex.getReason()).isEqualTo(reason);
                    assertThat(ex.getCouponCode()).isEqualTo(coupon.code());
                    assertThat(ex.getCode()).isEqualTo("COUPON_REJECTED");
                });
    }

    @Test
    void couponRejectsNegativeValue() {
        assertThatThrownBy(() -> Coupon.fixed("NEG", "-1")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void couponRejectsPercentageAboveHundred() {
        assertThatThrownBy(() -> Coupon.percentage("HUGE", "101")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void couponRejectsInvertedValidityWindow() {
        assertThatThrownBy(() -> Coupon.fixed("BAD", "1").withValidity(TODAY, TODAY.minusDays(1)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
