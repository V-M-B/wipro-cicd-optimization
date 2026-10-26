package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.Order;
import com.retailops.schemas.OrderLine;
import com.retailops.schemas.OrderStatus;

class OrderMapperTest {

    @Test
    void mapsOrderAndLinesInLineOrder() {
        OrderEntity entity = new OrderEntity("ord-9", "cus-3", null,
                TestFixtures.breakdown("60.00", "0.00", "4.80", "5.99", "70.79"), TestFixtures.NOW_UTC);
        entity.addLine(new OrderLineEntity(1, "APP-3001", 2, new BigDecimal("15.00"), new BigDecimal("30.00")));
        entity.addLine(new OrderLineEntity(2, "HOM-4001", 3, new BigDecimal("10.00"), new BigDecimal("30.00")));

        Order dto = OrderMapper.toDto(entity);

        assertThat(dto.id()).isEqualTo("ord-9");
        assertThat(dto.customerId()).isEqualTo("cus-3");
        assertThat(dto.status()).isEqualTo(OrderStatus.CREATED);
        assertThat(dto.couponCode()).isNull();
        assertThat(dto.createdAt()).isEqualTo(TestFixtures.NOW_UTC);
        assertThat(dto.total()).isEqualTo(new BigDecimal("70.79"));
        assertThat(dto.lines()).containsExactly(
                new OrderLine("APP-3001", 2, new BigDecimal("15.00"), new BigDecimal("30.00")),
                new OrderLine("HOM-4001", 3, new BigDecimal("10.00"), new BigDecimal("30.00")));
    }

    @Test
    void mapsSingleLine() {
        OrderLineEntity line = new OrderLineEntity(1, "TOY-5001", 1, new BigDecimal("44.99"), new BigDecimal("44.99"));
        assertThat(OrderMapper.toDto(line))
                .isEqualTo(new OrderLine("TOY-5001", 1, new BigDecimal("44.99"), new BigDecimal("44.99")));
    }

    @Test
    void orderWithoutLinesMapsToEmptyList() {
        OrderEntity entity = new OrderEntity("ord-0", "cus-0", "WELCOME10",
                TestFixtures.breakdown("0.00", "0.00", "0.00", "0.00", "0.00"), TestFixtures.NOW_UTC);
        Order dto = OrderMapper.toDto(entity);
        assertThat(dto.lines()).isEmpty();
        assertThat(dto.couponCode()).isEqualTo("WELCOME10");
    }
}
