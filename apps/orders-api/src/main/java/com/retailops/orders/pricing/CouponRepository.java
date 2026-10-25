package com.retailops.orders.pricing;

import java.time.LocalDate;
import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CouponRepository extends JpaRepository<CouponEntity, String> {

    @Query("""
            select c from CouponEntity c
            where c.active = true
              and (c.validFrom is null or c.validFrom <= :date)
              and (c.expiresOn is null or c.expiresOn >= :date)
            order by c.code""")
    List<CouponEntity> findRedeemableOn(@Param("date") LocalDate date);
}
