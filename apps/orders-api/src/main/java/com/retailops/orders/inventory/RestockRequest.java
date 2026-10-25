package com.retailops.orders.inventory;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

public record RestockRequest(@Min(1) @Max(InventoryService.MAX_RESTOCK) int quantity) {
}
