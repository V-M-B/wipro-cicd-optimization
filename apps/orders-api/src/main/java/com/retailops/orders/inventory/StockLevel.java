package com.retailops.orders.inventory;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Snapshot of stock for one SKU. Invariant: 0 <= reserved <= onHand. */
public record StockLevel(String sku, int onHand, int reserved) {

    public StockLevel {
        if (onHand < 0 || reserved < 0) {
            throw new IllegalArgumentException("stock quantities must not be negative");
        }
        if (reserved > onHand) {
            throw new IllegalArgumentException("reserved (" + reserved + ") exceeds on hand (" + onHand + ")");
        }
    }

    @JsonProperty("available")
    public int available() {
        return onHand - reserved;
    }

    public boolean canFulfil(int quantity) {
        return quantity > 0 && quantity <= available();
    }

    public boolean isOutOfStock() {
        return available() == 0;
    }
}
