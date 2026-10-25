package com.retailops.orders.order;

import java.util.Set;

import com.retailops.schemas.OrderStatus;

public class IllegalStatusTransitionException extends RuntimeException {

    private final OrderStatus from;
    private final OrderStatus to;
    private final Set<OrderStatus> allowed;

    public IllegalStatusTransitionException(OrderStatus from, OrderStatus to, Set<OrderStatus> allowed) {
        super("Cannot move order from " + from + " to " + to);
        this.from = from;
        this.to = to;
        this.allowed = Set.copyOf(allowed);
    }

    public OrderStatus getFrom() {
        return from;
    }

    public OrderStatus getTo() {
        return to;
    }

    public Set<OrderStatus> getAllowed() {
        return allowed;
    }
}
