package com.retailops.orders.customer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.Customer;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

class CustomerMapperTest {

    @Test
    void mapsAllFields() {
        CustomerEntity entity = new CustomerEntity("cus-0004", "Divya Menon", "divya.menon@example.com",
                CustomerTier.PLATINUM, Region.SOUTH, TestFixtures.NOW_UTC);
        assertThat(CustomerMapper.toDto(entity)).isEqualTo(new Customer("cus-0004", "Divya Menon",
                "divya.menon@example.com", CustomerTier.PLATINUM, Region.SOUTH));
    }

    @Test
    void entityRejectsNullTier() {
        CustomerEntity entity = new CustomerEntity("c", "n", "e@x.io", CustomerTier.GOLD, Region.EAST,
                TestFixtures.NOW_UTC);
        assertThatThrownBy(() -> entity.changeTier(null)).isInstanceOf(NullPointerException.class);
    }
}
