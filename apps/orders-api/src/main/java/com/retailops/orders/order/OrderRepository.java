package com.retailops.orders.order;

import java.math.BigDecimal;
import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.retailops.schemas.OrderStatus;

public interface OrderRepository extends JpaRepository<OrderEntity, String>, JpaSpecificationExecutor<OrderEntity> {

    long countByStatus(OrderStatus status);

    List<OrderEntity> findByCustomerIdOrderByCreatedAtDescIdAsc(String customerId);

    @Query("select coalesce(sum(o.total), 0) from OrderEntity o "
            + "where o.customerId = :customerId and o.status <> com.retailops.schemas.OrderStatus.CANCELLED")
    BigDecimal lifetimeValue(@Param("customerId") String customerId);

    @Query("select o.status as status, count(o) as orders from OrderEntity o "
            + "where o.customerId = :customerId group by o.status order by o.status")
    List<StatusCount> countByStatusForCustomer(@Param("customerId") String customerId);

    @Query("select l.sku as sku, sum(l.quantity) as units from OrderLineEntity l "
            + "where l.order.status <> com.retailops.schemas.OrderStatus.CANCELLED "
            + "group by l.sku order by sum(l.quantity) desc, l.sku asc")
    List<SkuUnits> unitsSoldBySku();

    interface StatusCount {
        OrderStatus getStatus();

        long getOrders();
    }

    interface SkuUnits {
        String getSku();

        long getUnits();
    }
}
