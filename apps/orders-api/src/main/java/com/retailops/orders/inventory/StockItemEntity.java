package com.retailops.orders.inventory;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "stock_items")
public class StockItemEntity {

    @Id
    @Column(length = 16)
    private String sku;

    @Column(name = "on_hand", nullable = false)
    private int onHand;

    @Column(nullable = false)
    private int reserved;

    protected StockItemEntity() {
    }

    public StockItemEntity(String sku, int onHand) {
        this.sku = sku;
        this.onHand = onHand;
        this.reserved = 0;
    }

    public StockLevel toLevel() {
        return new StockLevel(sku, onHand, reserved);
    }

    public String getSku() {
        return sku;
    }

    public int getOnHand() {
        return onHand;
    }

    public int getReserved() {
        return reserved;
    }
}
