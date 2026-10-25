package com.retailops.orders.validation;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

class SkuValidatorTest {

    @ParameterizedTest
    @ValueSource(strings = {"ELE-1001", "XYZ-999999", "TOY-12345"})
    void acceptsValidSkus(String sku) {
        assertThat(SkuValidator.isValid(sku)).isTrue();
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"ele-1001", "EL-1001", "ELEC-1001", "ELE1001", "ELE-123", "ELE-1234567",
            " ELE-1001", "ELE-١٢٣٤"})
    void rejectsInvalidSkus(String sku) {
        assertThat(SkuValidator.isValid(sku)).isFalse();
    }

    @ParameterizedTest
    @CsvSource({"' ele-1001 ', ELE-1001", "Gro-2001, GRO-2001"})
    void normalizeTrimsAndUpperCases(String raw, String expected) {
        assertThat(SkuValidator.normalize(raw)).isEqualTo(expected);
    }

    @Test
    void normalizeKeepsNull() {
        assertThat(SkuValidator.normalize(null)).isNull();
    }
}
