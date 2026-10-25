package com.retailops.orders.order;

import java.util.Collections;
import java.util.List;
import java.util.SortedMap;
import java.util.TreeMap;

import com.retailops.orders.common.BusinessRuleException;
import com.retailops.orders.validation.QuantityRules;
import com.retailops.orders.validation.SkuValidator;

/** Normalises request lines: upper-cases SKUs, merges duplicates, sorts by SKU. */
public final class OrderLines {

    public static final int MAX_DISTINCT_LINES = 50;

    private OrderLines() {
    }

    public static SortedMap<String, Integer> consolidate(List<OrderLineRequest> lines) {
        if (lines == null || lines.isEmpty()) {
            throw new BusinessRuleException("EMPTY_ORDER", "An order needs at least one line");
        }
        TreeMap<String, Integer> merged = new TreeMap<>();
        for (OrderLineRequest line : lines) {
            String sku = SkuValidator.normalize(line.sku());
            if (!SkuValidator.isValid(sku)) {
                throw new BusinessRuleException("INVALID_SKU", "Invalid SKU '" + line.sku() + "'");
            }
            QuantityRules.requireValid(line.quantity());
            merged.merge(sku, line.quantity(), Integer::sum);
        }
        merged.values().forEach(QuantityRules::requireValid);
        if (merged.size() > MAX_DISTINCT_LINES) {
            throw new BusinessRuleException("TOO_MANY_LINES",
                    "An order may contain at most " + MAX_DISTINCT_LINES + " distinct SKUs");
        }
        return Collections.unmodifiableSortedMap(merged);
    }
}
