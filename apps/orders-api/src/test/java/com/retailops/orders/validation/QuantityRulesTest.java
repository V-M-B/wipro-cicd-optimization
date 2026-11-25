package com.retailops.orders.validation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import com.retailops.orders.common.BusinessRuleException;

class QuantityRulesTest {

    @ParameterizedTest
    @ValueSource(ints = {1, 500, 999})
    void acceptsQuantitiesWithinBounds(int qty) {
        assertThat(QuantityRules.isValid(qty)).isTrue();
        assertThat(QuantityRules.requireInRange(qty)).isEqualTo(qty);
    }

    @ParameterizedTest
    @ValueSource(ints = {0, -1, 1000, Integer.MAX_VALUE})
    void rejectsQuantitiesOutsideBounds(int qty) {
        assertThat(QuantityRules.isValid(qty)).isFalse();
        assertThatThrownBy(() -> QuantityRules.requireInRange(qty))
                .isInstanceOfSatisfying(BusinessRuleException.class,
                        ex -> assertThat(ex.getCode()).isEqualTo("QUANTITY_OUT_OF_RANGE"));
    }
}
