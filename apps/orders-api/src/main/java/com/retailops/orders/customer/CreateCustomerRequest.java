package com.retailops.orders.customer;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import com.retailops.orders.validation.ValidEmail;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

public record CreateCustomerRequest(
        @NotBlank @Size(max = 120) String name,
        @ValidEmail String email,
        @NotNull CustomerTier tier,
        @NotNull Region region) {
}
