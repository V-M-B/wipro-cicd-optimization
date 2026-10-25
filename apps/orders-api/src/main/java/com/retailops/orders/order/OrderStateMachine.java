package com.retailops.orders.order;

import java.util.Collections;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import com.retailops.schemas.OrderStatus;

/**
 * Order lifecycle: CREATED -> PAID -> SHIPPED -> DELIVERED, and CREATED/PAID -> CANCELLED.
 * DELIVERED and CANCELLED are terminal. Self-transitions are illegal.
 */
public final class OrderStateMachine {

    private static final Map<OrderStatus, Set<OrderStatus>> TRANSITIONS;

    static {
        EnumMap<OrderStatus, Set<OrderStatus>> t = new EnumMap<>(OrderStatus.class);
        t.put(OrderStatus.CREATED, Collections.unmodifiableSet(EnumSet.of(OrderStatus.PAID, OrderStatus.CANCELLED)));
        t.put(OrderStatus.PAID, Collections.unmodifiableSet(EnumSet.of(OrderStatus.SHIPPED, OrderStatus.CANCELLED)));
        t.put(OrderStatus.SHIPPED, Collections.unmodifiableSet(EnumSet.of(OrderStatus.DELIVERED)));
        t.put(OrderStatus.DELIVERED, Collections.unmodifiableSet(EnumSet.noneOf(OrderStatus.class)));
        t.put(OrderStatus.CANCELLED, Collections.unmodifiableSet(EnumSet.noneOf(OrderStatus.class)));
        TRANSITIONS = Collections.unmodifiableMap(t);
    }

    private OrderStateMachine() {
    }

    public static Set<OrderStatus> allowedTargets(OrderStatus from) {
        return TRANSITIONS.get(Objects.requireNonNull(from, "from"));
    }

    public static boolean canTransition(OrderStatus from, OrderStatus to) {
        return to != null && allowedTargets(from).contains(to);
    }

    public static boolean isTerminal(OrderStatus status) {
        return allowedTargets(status).isEmpty();
    }

    /** Returns {@code to} if the transition is legal, otherwise throws. */
    public static OrderStatus transition(OrderStatus from, OrderStatus to) {
        Objects.requireNonNull(to, "to");
        if (!canTransition(from, to)) {
            throw new IllegalStatusTransitionException(from, to, allowedTargets(from));
        }
        return to;
    }

    /** Whether reaching {@code to} from {@code from} releases reserved stock back to inventory. */
    public static boolean releasesStock(OrderStatus from, OrderStatus to) {
        return to == OrderStatus.CANCELLED && canTransition(from, to);
    }

    /** Whether reaching {@code to} consumes reserved stock (goods leave the warehouse). */
    public static boolean consumesStock(OrderStatus from, OrderStatus to) {
        return to == OrderStatus.SHIPPED && canTransition(from, to);
    }
}
