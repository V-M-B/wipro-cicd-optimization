package com.retailops.orders.order;

import com.retailops.schemas.Order;
import com.retailops.schemas.OrderLine;

public final class OrderMapper {

    private OrderMapper() {
    }

    public static Order toDto(OrderEntity entity) {
        return new Order(entity.getId(), entity.getCustomerId(), entity.getStatus(),
                entity.getLines().stream().map(OrderMapper::toDto).toList(),
                entity.getCouponCode(), entity.getCreatedAt(), entity.getTotal());
    }

    public static OrderLine toDto(OrderLineEntity line) {
        return new OrderLine(line.getSku(), line.getQuantity(), line.getUnitPrice());
    }
}
