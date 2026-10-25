package com.retailops.orders.catalog;

import java.math.BigDecimal;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import com.retailops.orders.inventory.InventoryService;
import com.retailops.orders.validation.ValidSku;
import com.retailops.schemas.Category;

public record CreateProductRequest(
        @ValidSku String sku,
        @NotBlank @Size(max = 120) String name,
        @NotNull Category category,
        @NotNull @DecimalMin("0.01") @Digits(integer = 10, fraction = 2) BigDecimal unitPrice,
        @PositiveOrZero @Max(InventoryService.MAX_RESTOCK) int initialStock) {
}
