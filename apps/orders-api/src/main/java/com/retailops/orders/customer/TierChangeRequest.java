package com.retailops.orders.customer;

import jakarta.validation.constraints.NotNull;

import com.retailops.schemas.CustomerTier;

public record TierChangeRequest(@NotNull CustomerTier tier) {
}
