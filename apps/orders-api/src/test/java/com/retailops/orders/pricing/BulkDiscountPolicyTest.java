package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class BulkDiscountPolicyTest {

    private final BulkDiscountPolicy policy = new BulkDiscountPolicy();

    @ParameterizedTest(name = "qty {0} -> rate {1}")
    @CsvSource({
            "0, 0.00", "9, 0.00", "10, 0.02", "19, 0.02",
            "20, 0.05", "50, 0.08", "100, 0.12"
    })
    void rateBoundaries(int quantity, String rate) {
        assertThat(policy.rate(quantity)).isEqualByComparingTo(rate);
    }

    @ParameterizedTest(name = "{0} at qty {1} -> {2}")
    @CsvSource({
            "100.00, 10, 2.00",
            "250.00, 20, 12.50",
            "33.33, 50, 2.67",
            "1000.00, 100, 120.00",
            "49.99, 9, 0.00"
    })
    void discountOnLineSubtotal(String lineSubtotal, int quantity, String expected) {
        assertThat(policy.discount(new BigDecimal(lineSubtotal), quantity)).isEqualTo(new BigDecimal(expected));
    }

    @Test
    void negativeQuantityIsRejected() {
        assertThatThrownBy(() -> policy.rate(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}
