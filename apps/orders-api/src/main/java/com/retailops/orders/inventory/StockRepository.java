package com.retailops.orders.inventory;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/**
 * Stock mutations are single conditional UPDATE statements so concurrent reservations cannot
 * oversell: the row lock plus the re-checked WHERE clause serialise competing writers.
 */
public interface StockRepository extends JpaRepository<StockItemEntity, String> {

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update StockItemEntity s set s.reserved = s.reserved + :qty "
            + "where s.sku = :sku and s.onHand - s.reserved >= :qty")
    int tryReserve(@Param("sku") String sku, @Param("qty") int quantity);

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update StockItemEntity s set s.reserved = s.reserved - :qty where s.sku = :sku and s.reserved >= :qty")
    int release(@Param("sku") String sku, @Param("qty") int quantity);

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update StockItemEntity s set s.onHand = s.onHand - :qty, s.reserved = s.reserved - :qty "
            + "where s.sku = :sku and s.reserved >= :qty")
    int commitReserved(@Param("sku") String sku, @Param("qty") int quantity);

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update StockItemEntity s set s.onHand = s.onHand + :qty where s.sku = :sku")
    int restock(@Param("sku") String sku, @Param("qty") int quantity);

    @Query("select s from StockItemEntity s where s.onHand - s.reserved <= :threshold order by s.sku")
    List<StockItemEntity> findLowStock(@Param("threshold") int threshold);
}
