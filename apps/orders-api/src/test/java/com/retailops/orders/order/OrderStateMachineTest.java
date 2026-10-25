package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.MethodSource;

import com.retailops.schemas.OrderStatus;

/** Exhaustive check of all 25 (from, to) status pairs against the documented lifecycle. */
class OrderStateMachineTest {

    private static final Set<String> LEGAL = Set.of(
            "CREATED->PAID", "CREATED->CANCELLED",
            "PAID->SHIPPED", "PAID->CANCELLED",
            "SHIPPED->DELIVERED");

    static Stream<Arguments> allPairs() {
        List<Arguments> pairs = new ArrayList<>();
        for (OrderStatus from : OrderStatus.values()) {
            for (OrderStatus to : OrderStatus.values()) {
                pairs.add(Arguments.of(from, to, LEGAL.contains(from + "->" + to)));
            }
        }
        return pairs.stream();
    }

    static Stream<Arguments> legalPairs() {
        return allPairs().filter(a -> (boolean) a.get()[2]);
    }

    static Stream<Arguments> illegalPairs() {
        return allPairs().filter(a -> !(boolean) a.get()[2]);
    }

    @ParameterizedTest(name = "{0} -> {1} succeeds")
    @MethodSource("legalPairs")
    void legalTransitionsReturnTarget(OrderStatus from, OrderStatus to, boolean legal) {
        assertThat(OrderStateMachine.canTransition(from, to)).isTrue();
        assertThat(OrderStateMachine.transition(from, to)).isEqualTo(to);
    }

    @ParameterizedTest(name = "{0} -> {1} rejected")
    @MethodSource("illegalPairs")
    void illegalTransitionsAreRejected(OrderStatus from, OrderStatus to, boolean legal) {
        assertThat(OrderStateMachine.canTransition(from, to)).isFalse();
        assertThatThrownBy(() -> OrderStateMachine.transition(from, to))
                .isInstanceOfSatisfying(IllegalStatusTransitionException.class, ex -> {
                    assertThat(ex.getFrom()).isEqualTo(from);
                    assertThat(ex.getTo()).isEqualTo(to);
                    assertThat(ex.getAllowed()).isEqualTo(OrderStateMachine.allowedTargets(from));
                });
    }

    @ParameterizedTest
    @CsvSource({"CREATED, false", "PAID, false", "SHIPPED, false", "DELIVERED, true", "CANCELLED, true"})
    void terminalStates(OrderStatus status, boolean terminal) {
        assertThat(OrderStateMachine.isTerminal(status)).isEqualTo(terminal);
    }

    @Test
    void cancellingReleasesStockOnlyFromCreatedOrPaid() {
        assertThat(OrderStateMachine.releasesStock(OrderStatus.CREATED, OrderStatus.CANCELLED)).isTrue();
        assertThat(OrderStateMachine.releasesStock(OrderStatus.PAID, OrderStatus.CANCELLED)).isTrue();
        assertThat(OrderStateMachine.releasesStock(OrderStatus.SHIPPED, OrderStatus.CANCELLED)).isFalse();
        assertThat(OrderStateMachine.releasesStock(OrderStatus.CREATED, OrderStatus.PAID)).isFalse();
    }

    @Test
    void onlyShippingConsumesStock() {
        assertThat(OrderStateMachine.consumesStock(OrderStatus.PAID, OrderStatus.SHIPPED)).isTrue();
        assertThat(OrderStateMachine.consumesStock(OrderStatus.CREATED, OrderStatus.SHIPPED)).isFalse();
        assertThat(OrderStateMachine.consumesStock(OrderStatus.SHIPPED, OrderStatus.DELIVERED)).isFalse();
    }

    @Test
    void allowedTargetsAreImmutable() {
        assertThatThrownBy(() -> OrderStateMachine.allowedTargets(OrderStatus.CREATED).add(OrderStatus.DELIVERED))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void nullTargetIsRejected() {
        assertThat(OrderStateMachine.canTransition(OrderStatus.CREATED, null)).isFalse();
        assertThatThrownBy(() -> OrderStateMachine.transition(OrderStatus.CREATED, null))
                .isInstanceOf(NullPointerException.class);
    }

    @Test
    void happyPathReachesDelivered() {
        OrderStatus s = OrderStatus.CREATED;
        for (OrderStatus next : List.of(OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED)) {
            s = OrderStateMachine.transition(s, next);
        }
        assertThat(s).isEqualTo(OrderStatus.DELIVERED);
        assertThat(OrderStateMachine.isTerminal(s)).isTrue();
    }
}
