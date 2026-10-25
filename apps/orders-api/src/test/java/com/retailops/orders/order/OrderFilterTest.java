package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

import com.retailops.orders.common.BusinessRuleException;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.OrderStatus;

class OrderFilterTest {

    @Test
    void noneIsEmpty() {
        assertThat(OrderFilter.none().isEmpty()).isTrue();
        assertThat(OrderFilter.none().toSpecification()).isNotNull();
    }

    @Test
    void blankCustomerIdIsIgnored() {
        assertThat(new OrderFilter("  ", null, null, null).customerId()).isNull();
    }

    @Test
    void anyCriterionMakesFilterNonEmpty() {
        assertThat(new OrderFilter(null, OrderStatus.PAID, null, null).isEmpty()).isFalse();
        assertThat(new OrderFilter("cus-1", null, null, null).isEmpty()).isFalse();
        assertThat(new OrderFilter(null, null, TestFixtures.NOW_UTC, null).isEmpty()).isFalse();
    }

    @Test
    void fromMustBeBeforeTo() {
        assertThatThrownBy(() -> new OrderFilter(null, null, TestFixtures.NOW_UTC, TestFixtures.NOW_UTC.minusDays(1)))
                .isInstanceOfSatisfying(BusinessRuleException.class,
                        ex -> assertThat(ex.getCode()).isEqualTo("INVALID_DATE_RANGE"));
    }

    @Test
    void emptyRangeIsRejected() {
        assertThatThrownBy(() -> new OrderFilter(null, null, TestFixtures.NOW_UTC, TestFixtures.NOW_UTC))
                .isInstanceOf(BusinessRuleException.class);
    }
}
