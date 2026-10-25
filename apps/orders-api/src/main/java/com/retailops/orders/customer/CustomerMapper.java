package com.retailops.orders.customer;

import com.retailops.schemas.Customer;

public final class CustomerMapper {

    private CustomerMapper() {
    }

    public static Customer toDto(CustomerEntity entity) {
        return new Customer(entity.getId(), entity.getName(), entity.getEmail(), entity.getTier(),
                entity.getRegion());
    }
}
