package com.retailops.orders.catalog;

import com.retailops.schemas.Product;

public final class ProductMapper {

    private ProductMapper() {
    }

    public static Product toDto(ProductEntity entity) {
        return new Product(entity.getId(), entity.getSku(), entity.getName(), entity.getCategory(),
                entity.getUnitPrice(), entity.isActive());
    }
}
