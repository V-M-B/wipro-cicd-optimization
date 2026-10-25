package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import com.retailops.schemas.CustomerTier;

class TierDiscountPolicyTest {

    private final TierDiscountPolicy policy = new TierDiscountPolicy();

    @ParameterizedTest
    @CsvSource({"STANDARD, 0.00", "SILVER, 0.05", "GOLD, 0.10", "PLATINUM, 0.15"})
    void rateByTier(CustomerTier tier, String rate) {
        assertThat(policy.rate(tier)).isEqualByComparingTo(rate);
    }

    @ParameterizedTest(name = "{0} on {1} -> {2}")
    @CsvSource({
            "SILVER, 19.99, 1.00",
            "GOLD, 0.05, 0.00",
            "GOLD, 0.15, 0.02",
            "SILVER, 0.10, 0.00",
            "PLATINUM, 1234.56, 185.18"
    })
    void discountIsRoundedHalfEven(CustomerTier tier, String amount, String expected) {
        assertThat(policy.discount(new BigDecimal(amount), tier)).isEqualTo(new BigDecimal(expected));
    }

    @Test
    void higherTiersNeverDiscountLess() {
        BigDecimal previous = BigDecimal.valueOf(-1);
        for (CustomerTier tier : CustomerTier.values()) {
            assertThat(policy.rate(tier)).isGreaterThan(previous);
            previous = policy.rate(tier);
        }
    }

    @Test
    void nullTierIsRejected() {
        assertThatThrownBy(() -> policy.rate(null)).isInstanceOf(NullPointerException.class);
    }
}
