package com.retailops.orders.inventory;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;

@Service
public class InventoryService {

    public static final int MAX_RESTOCK = 100_000;

    private final StockRepository stockRepository;

    public InventoryService(StockRepository stockRepository) {
        this.stockRepository = stockRepository;
    }

    @Transactional(readOnly = true)
    public StockLevel level(String sku) {
        return stockRepository.findById(sku)
                .map(StockItemEntity::toLevel)
                .orElseThrow(() -> new NotFoundException("Stock", sku));
    }

    @Transactional(readOnly = true)
    public List<StockLevel> lowStock(int threshold) {
        if (threshold < 0) {
            throw new IllegalArgumentException("threshold must not be negative");
        }
        return stockRepository.findLowStock(threshold).stream().map(StockItemEntity::toLevel).toList();
    }

    @Transactional
    public StockLevel register(String sku, int initialOnHand) {
        if (initialOnHand < 0 || initialOnHand > MAX_RESTOCK) {
            throw new IllegalArgumentException("initial stock out of range: " + initialOnHand);
        }
        if (stockRepository.existsById(sku)) {
            throw new DuplicateResourceException("Stock", sku);
        }
        return stockRepository.save(new StockItemEntity(sku, initialOnHand)).toLevel();
    }

    /** Reserves stock or throws {@link InsufficientStockException}. */
    @Transactional
    public void reserve(String sku, int quantity) {
        requirePositive(quantity);
        if (stockRepository.tryReserve(sku, quantity) == 0) {
            StockLevel level = level(sku);
            throw new InsufficientStockException(sku, quantity, level.available());
        }
    }

    @Transactional
    public void release(String sku, int quantity) {
        requirePositive(quantity);
        if (stockRepository.release(sku, quantity) == 0) {
            level(sku);
            throw new IllegalStateException("Cannot release " + quantity + " of '" + sku + "': not reserved");
        }
    }

    /** Ships reserved stock: removes it from both on-hand and reserved. */
    @Transactional
    public void commit(String sku, int quantity) {
        requirePositive(quantity);
        if (stockRepository.commitReserved(sku, quantity) == 0) {
            level(sku);
            throw new IllegalStateException("Cannot commit " + quantity + " of '" + sku + "': not reserved");
        }
    }

    @Transactional
    public StockLevel restock(String sku, int quantity) {
        if (quantity <= 0 || quantity > MAX_RESTOCK) {
            throw new IllegalArgumentException("restock quantity out of range: " + quantity);
        }
        if (stockRepository.restock(sku, quantity) == 0) {
            throw new NotFoundException("Stock", sku);
        }
        return level(sku);
    }

    private static void requirePositive(int quantity) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be positive: " + quantity);
        }
    }
}
