package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.util.Objects;

/** One priced order line: SKU, quantity and the catalog unit price at pricing time. */
public record PricedLine(String sku, int quantity, BigDecimal unitPrice) {

    public PricedLine {
        Objects.requireNonNull(sku, "sku");
        Objects.requireNonNull(unitPrice, "unitPrice");
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be positive: " + quantity);
        }
        if (unitPrice.signum() < 0) {
            throw new IllegalArgumentException("unit price must not be negative: " + unitPrice);
        }
    }

    public BigDecimal lineSubtotal() {
        return Money.round(unitPrice.multiply(BigDecimal.valueOf(quantity)));
    }
}
