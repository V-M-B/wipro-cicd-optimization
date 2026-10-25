package com.retailops.orders.customer;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

public interface CustomerRepository extends JpaRepository<CustomerEntity, String> {

    boolean existsByEmailIgnoreCase(String email);

    List<CustomerEntity> findAllByOrderByNameAscIdAsc();

    List<CustomerEntity> findByTierOrderByNameAscIdAsc(CustomerTier tier);

    long countByRegion(Region region);
}
