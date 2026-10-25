package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import com.retailops.schemas.Region;

class TaxPolicyTest {

    private final TaxPolicy policy = new TaxPolicy(PricingProperties.defaults());

    @ParameterizedTest
    @CsvSource({"NORTH, 0.0800", "SOUTH, 0.0650", "EAST, 0.0725", "WEST, 0.0900"})
    void defaultRates(Region region, String rate) {
        assertThat(policy.rate(region)).isEqualByComparingTo(rate);
    }

    @ParameterizedTest(name = "{0}: tax on {1} = {2}")
    @CsvSource({
            "EAST, 19.99, 1.45",
            "SOUTH, 10.10, 0.66",
            "NORTH, 0.00, 0.00",
            "WEST, 55.55, 5.00",
            "EAST, 1.00, 0.07",
            "SOUTH, 0.10, 0.01"
    })
    void taxIsRoundedHalfEven(Region region, String amount, String expected) {
        assertThat(policy.tax(new BigDecimal(amount), region)).isEqualTo(new BigDecimal(expected));
    }

    @Test
    void overriddenRateIsUsed() {
        TaxPolicy custom = new TaxPolicy(new PricingProperties(null,
                Map.of(Region.WEST, new BigDecimal("0.1000")), null, null, null));
        assertThat(custom.tax(new BigDecimal("100.00"), Region.WEST)).isEqualTo(new BigDecimal("10.00"));
        assertThat(custom.tax(new BigDecimal("100.00"), Region.NORTH)).isEqualTo(new BigDecimal("8.00"));
    }

    @Test
    void negativeTaxableAmountIsRejected() {
        assertThatThrownBy(() -> policy.tax(new BigDecimal("-1.00"), Region.EAST))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
