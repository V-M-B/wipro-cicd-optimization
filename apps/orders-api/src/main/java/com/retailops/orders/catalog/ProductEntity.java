package com.retailops.orders.catalog;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import com.retailops.schemas.Category;

@Entity
@Table(name = "products")
public class ProductEntity {

    @Id
    @Column(length = 40)
    private String id;

    @Column(nullable = false, unique = true, length = 16)
    private String sku;

    @Column(nullable = false, length = 120)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private Category category;

    @Column(name = "unit_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(nullable = false)
    private boolean active;

    @Column(name = "created_at", nullable = false)
    private OffsetDateTime createdAt;

    protected ProductEntity() {
    }

    public ProductEntity(String id, String sku, String name, Category category, BigDecimal unitPrice,
            OffsetDateTime createdAt) {
        this.id = id;
        this.sku = sku;
        this.name = name;
        this.category = category;
        this.unitPrice = unitPrice;
        this.active = true;
        this.createdAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public String getSku() {
        return sku;
    }

    public String getName() {
        return name;
    }

    public Category getCategory() {
        return category;
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public boolean isActive() {
        return active;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void changePrice(BigDecimal newPrice) {
        if (newPrice == null || newPrice.signum() <= 0) {
            throw new IllegalArgumentException("price must be positive");
        }
        this.unitPrice = newPrice;
    }

    public void deactivate() {
        this.active = false;
    }
}
