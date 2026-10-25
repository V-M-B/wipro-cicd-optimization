package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import java.util.SortedMap;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import com.retailops.orders.common.BusinessRuleException;

class OrderLinesTest {

    private static OrderLineRequest l(String sku, int qty) {
        return new OrderLineRequest(sku, qty);
    }

    private static void assertCode(Runnable r, String code) {
        assertThatThrownBy(r::run).isInstanceOfSatisfying(BusinessRuleException.class,
                ex -> assertThat(ex.getCode()).isEqualTo(code));
    }

    @Test
    void mergesDuplicateSkus() {
        SortedMap<String, Integer> merged = OrderLines.consolidate(List.of(l("ELE-1001", 2), l("ELE-1001", 3)));
        assertThat(merged).containsExactlyEntriesOf(java.util.Map.of("ELE-1001", 5));
    }

    @Test
    void normalisesCaseAndWhitespaceBeforeMerging() {
        SortedMap<String, Integer> merged = OrderLines.consolidate(List.of(l(" ele-1001 ", 1), l("ELE-1001", 1)));
        assertThat(merged).containsOnlyKeys("ELE-1001").containsValue(2);
    }

    @Test
    void resultIsSortedBySku() {
        SortedMap<String, Integer> merged = OrderLines.consolidate(
                List.of(l("TOY-5001", 1), l("APP-3001", 1), l("HOM-4001", 1)));
        assertThat(merged.keySet()).containsExactly("APP-3001", "HOM-4001", "TOY-5001");
    }

    @Test
    void resultIsUnmodifiable() {
        SortedMap<String, Integer> merged = OrderLines.consolidate(List.of(l("ELE-1001", 1)));
        assertThatThrownBy(() -> merged.put("X", 1)).isInstanceOf(UnsupportedOperationException.class);
    }

    @ParameterizedTest
    @ValueSource(strings = {"ELE1001", ""})
    void invalidSkuIsRejected(String sku) {
        assertCode(() -> OrderLines.consolidate(List.of(l(sku, 1))), "INVALID_SKU");
    }

    @ParameterizedTest
    @ValueSource(ints = {0, 1000})
    void lineQuantityOutOfRangeIsRejected(int qty) {
        assertCode(() -> OrderLines.consolidate(List.of(l("ELE-1001", qty))), "QUANTITY_OUT_OF_RANGE");
    }

    @Test
    void mergedQuantityAboveMaximumIsRejected() {
        assertCode(() -> OrderLines.consolidate(List.of(l("ELE-1001", 600), l("ELE-1001", 400))),
                "QUANTITY_OUT_OF_RANGE");
    }

    @Test
    void emptyOrNullLinesAreRejected() {
        assertCode(() -> OrderLines.consolidate(List.of()), "EMPTY_ORDER");
        assertCode(() -> OrderLines.consolidate(null), "EMPTY_ORDER");
    }

    @Test
    void fiftyDistinctSkusAreAllowedButFiftyOneAreNot() {
        List<OrderLineRequest> fifty = IntStream.rangeClosed(1, 50).mapToObj(i -> l("BLK-%04d".formatted(i), 1)).toList();
        assertThat(OrderLines.consolidate(fifty)).hasSize(50);
        List<OrderLineRequest> fiftyOne = IntStream.rangeClosed(1, 51).mapToObj(i -> l("BLK-%04d".formatted(i), 1)).toList();
        assertCode(() -> OrderLines.consolidate(fiftyOne), "TOO_MANY_LINES");
    }
}
