package com.retailops.orders.customer;

import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

@Entity
@Table(name = "customers")
public class CustomerEntity {

    @Id
    @Column(length = 40)
    private String id;

    @Column(nullable = false, length = 120)
    private String name;

    @Column(nullable = false, unique = true, length = 254)
    private String email;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private CustomerTier tier;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private Region region;

    @Column(name = "created_at", nullable = false)
    private OffsetDateTime createdAt;

    protected CustomerEntity() {
    }

    public CustomerEntity(String id, String name, String email, CustomerTier tier, Region region,
            OffsetDateTime createdAt) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.tier = tier;
        this.region = region;
        this.createdAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getEmail() {
        return email;
    }

    public CustomerTier getTier() {
        return tier;
    }

    public Region getRegion() {
        return region;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void changeTier(CustomerTier newTier) {
        this.tier = java.util.Objects.requireNonNull(newTier, "tier");
    }
}
