package com.retailops.orders.catalog;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.Category;
import com.retailops.schemas.Product;

class ProductMapperTest {

    @Test
    void mapsAllFields() {
        ProductEntity entity = new ProductEntity("prd-1", "ELE-1001", "Wireless Mouse", Category.ELECTRONICS,
                new BigDecimal("24.99"), TestFixtures.NOW_UTC);
        assertThat(ProductMapper.toDto(entity)).isEqualTo(
                new Product("prd-1", "ELE-1001", "Wireless Mouse", Category.ELECTRONICS, new BigDecimal("24.99"), true));
    }

    @Test
    void mapsInactiveFlag() {
        ProductEntity entity = new ProductEntity("prd-2", "TOY-5008", "Yo-Yo", Category.TOYS, new BigDecimal("2.50"),
                TestFixtures.NOW_UTC);
        entity.deactivate();
        assertThat(ProductMapper.toDto(entity).active()).isFalse();
    }
}
