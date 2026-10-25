package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

import com.retailops.orders.pricing.PriceBreakdown;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.OrderStatus;

class OrderEntityTest {

    private final PriceBreakdown price = new PriceBreakdown(new BigDecimal("100.00"), new BigDecimal("2.00"),
            new BigDecimal("4.90"), new BigDecimal("3.10"), new BigDecimal("7.20"), new BigDecimal("0.00"),
            new BigDecimal("97.20"));

    private OrderEntity newOrder() {
        return new OrderEntity("ord-1", "cus-1", "SAVE5", price, TestFixtures.NOW_UTC);
    }

    @Test
    void newOrderStartsCreatedWithPricedTotals() {
        OrderEntity order = newOrder();
        assertThat(order.getStatus()).isEqualTo(OrderStatus.CREATED);
        assertThat(order.getSubtotal()).isEqualTo(new BigDecimal("100.00"));
        assertThat(order.getDiscountTotal()).isEqualTo(new BigDecimal("10.00"));
        assertThat(order.getTaxTotal()).isEqualTo(new BigDecimal("7.20"));
        assertThat(order.getTotal()).isEqualTo(new BigDecimal("97.20"));
        assertThat(order.getCreatedAt()).isEqualTo(order.getUpdatedAt());
    }

    @Test
    void addLineAttachesBackReference() {
        OrderEntity order = newOrder();
        OrderLineEntity line = new OrderLineEntity(1, "ELE-1001", 4, new BigDecimal("25.00"), new BigDecimal("100.00"));
        order.addLine(line);
        assertThat(line.getOrder()).isSameAs(order);
        assertThat(order.getLines()).containsExactly(line);
        assertThat(order.totalUnits()).isEqualTo(4);
    }

    @Test
    void transitionUpdatesStatusAndTimestamp() {
        OrderEntity order = newOrder();
        OrderStatus previous = order.transitionTo(OrderStatus.PAID, TestFixtures.NOW_UTC.plusHours(1));
        assertThat(previous).isEqualTo(OrderStatus.CREATED);
        assertThat(order.getStatus()).isEqualTo(OrderStatus.PAID);
        assertThat(order.getUpdatedAt()).isEqualTo(TestFixtures.NOW_UTC.plusHours(1));
    }

    @Test
    void illegalTransitionLeavesOrderUnchanged() {
        OrderEntity order = newOrder();
        assertThatThrownBy(() -> order.transitionTo(OrderStatus.DELIVERED, TestFixtures.NOW_UTC.plusHours(1)))
                .isInstanceOf(IllegalStatusTransitionException.class);
        assertThat(order.getStatus()).isEqualTo(OrderStatus.CREATED);
        assertThat(order.getUpdatedAt()).isEqualTo(TestFixtures.NOW_UTC);
    }

    @Test
    void linesViewIsReadOnly() {
        OrderEntity order = newOrder();
        assertThatThrownBy(() -> order.getLines().add(null)).isInstanceOf(UnsupportedOperationException.class);
    }
}
