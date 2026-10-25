package com.retailops.orders.inventory;

import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/inventory")
public class InventoryController {

    private final InventoryService inventoryService;

    public InventoryController(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    @GetMapping("/{sku}")
    public StockLevel level(@PathVariable String sku) {
        return inventoryService.level(sku);
    }

    @GetMapping("/low-stock")
    public List<StockLevel> lowStock(@RequestParam(defaultValue = "10") @Min(0) @Max(100_000) int threshold) {
        return inventoryService.lowStock(threshold);
    }

    @PostMapping("/{sku}/restock")
    public StockLevel restock(@PathVariable String sku, @Valid @RequestBody RestockRequest request) {
        return inventoryService.restock(sku, request.quantity());
    }
}
