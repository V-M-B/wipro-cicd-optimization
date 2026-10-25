package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class MoneyTest {

    @ParameterizedTest(name = "round({0}) = {1}")
    @CsvSource({
            "1.005, 1.00",
            "1.015, 1.02",
            "2.675, 2.68",
            "-1.005, -1.00",
            "-1.015, -1.02",
            "10, 10.00"
    })
    void roundsHalfEvenToTwoDecimals(String input, String expected) {
        BigDecimal rounded = Money.round(new BigDecimal(input));
        assertThat(rounded).isEqualTo(new BigDecimal(expected));
        assertThat(rounded.scale()).isEqualTo(2);
    }

    @ParameterizedTest(name = "{0} x {1} = {2}")
    @CsvSource({
            "100.00, 0.05, 5.00",
            "19.99, 0.0725, 1.45",
            "10.10, 0.065, 0.66",
            "0.50, 0.05, 0.02",
            "33.33, 0.15, 5.00"
    })
    void percentOfRoundsResult(String amount, String rate, String expected) {
        assertThat(Money.percentOf(new BigDecimal(amount), new BigDecimal(rate))).isEqualTo(new BigDecimal(expected));
    }

    @Test
    void zeroHasScaleTwo() {
        assertThat(Money.ZERO).isEqualTo(new BigDecimal("0.00"));
    }

    @Test
    void ofParsesAndRounds() {
        assertThat(Money.of("12.345")).isEqualTo(new BigDecimal("12.34"));
    }

    @Test
    void minAndMaxCompareByValue() {
        assertThat(Money.min(new BigDecimal("1.50"), new BigDecimal("1.5"))).isEqualByComparingTo("1.5");
        assertThat(Money.min(new BigDecimal("2.00"), new BigDecimal("3.00"))).isEqualTo(new BigDecimal("2.00"));
        assertThat(Money.max(new BigDecimal("2.00"), new BigDecimal("3.00"))).isEqualTo(new BigDecimal("3.00"));
    }

    @Test
    void isNegativeDetectsSign() {
        assertThat(Money.isNegative(new BigDecimal("-0.01"))).isTrue();
        assertThat(Money.isNegative(Money.ZERO)).isFalse();
    }

    @Test
    void sumAddsAndRoundsToCents() {
        assertThat(Money.sum(new BigDecimal("1.10"), new BigDecimal("2.205"), new BigDecimal("-0.30")))
                .isEqualTo(new BigDecimal("3.00"));
        assertThat(Money.sum(new BigDecimal("19.99"))).isEqualTo(new BigDecimal("19.99"));
    }

    @Test
    void sumOfNothingIsZero() {
        assertThat(Money.sum()).isEqualTo(Money.ZERO);
    }

    @Test
    void sumRejectsNullAmounts() {
        assertThatThrownBy(() -> Money.sum(Money.ZERO, null)).isInstanceOf(NullPointerException.class);
    }

    @Test
    void roundRejectsNull() {
        assertThatThrownBy(() -> Money.round(null)).isInstanceOf(NullPointerException.class);
    }
}
