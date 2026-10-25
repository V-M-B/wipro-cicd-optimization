package com.retailops.orders.validation;

import com.retailops.orders.common.BusinessRuleException;

/** Bounds for a single order line quantity. */
public final class QuantityRules {

    public static final int MIN = 1;
    public static final int MAX = 999;

    private QuantityRules() {
    }

    public static boolean isValid(int quantity) {
        return quantity >= MIN && quantity <= MAX;
    }

    public static int requireValid(int quantity) {
        if (!isValid(quantity)) {
            throw new BusinessRuleException("QUANTITY_OUT_OF_RANGE",
                    "Quantity " + quantity + " is outside the allowed range " + MIN + ".." + MAX);
        }
        return quantity;
    }
}
