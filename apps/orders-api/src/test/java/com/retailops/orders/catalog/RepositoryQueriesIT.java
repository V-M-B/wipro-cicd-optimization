package com.retailops.orders.catalog;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;

import com.retailops.orders.customer.CustomerEntity;
import com.retailops.orders.customer.CustomerRepository;
import com.retailops.orders.inventory.StockItemEntity;
import com.retailops.orders.inventory.StockRepository;
import com.retailops.orders.order.OrderEntity;
import com.retailops.orders.order.OrderFilter;
import com.retailops.orders.order.OrderLineEntity;
import com.retailops.orders.order.OrderRepository;
import com.retailops.orders.pricing.CouponEntity;
import com.retailops.orders.pricing.CouponRepository;
import com.retailops.orders.pricing.PriceBreakdown;
import com.retailops.orders.support.PostgresTestcontainersConfig;
import com.retailops.schemas.Category;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.OrderStatus;

/** JPA slice against real PostgreSQL + Flyway seed data; each test rolls back. */
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import(PostgresTestcontainersConfig.class)
class RepositoryQueriesIT {

    @Autowired
    ProductRepository products;
    @Autowired
    CustomerRepository customers;
    @Autowired
    CouponRepository coupons;
    @Autowired
    StockRepository stock;
    @Autowired
    OrderRepository orders;

    @Test
    void lookupBySkuListIgnoresUnknownSkus() {
        assertThat(products.findBySkuIn(List.of("ELE-1001", "TOY-5008", "NOP-0000")))
                .extracting(ProductEntity::getSku).containsExactlyInAnyOrder("ELE-1001", "TOY-5008");
    }

    @Test
    void activeProductCountPerCategory() {
        Map<Category, Long> counts = products.countActiveByCategory().stream()
                .collect(Collectors.toMap(ProductRepository.CategoryCount::getCategory,
                        ProductRepository.CategoryCount::getProducts));
        assertThat(counts).containsExactlyInAnyOrderEntriesOf(Map.of(Category.ELECTRONICS, 8L, Category.GROCERY, 8L,
                Category.APPAREL, 8L, Category.HOME, 8L, Category.TOYS, 7L));
    }

    @Test
    void customersByTierAreSortedByName() {
        assertThat(customers.findByTierOrderByNameAscIdAsc(CustomerTier.GOLD)).extracting(CustomerEntity::getName)
                .containsExactly("Chen Wei", "Grace Kim", "Kavya Iyer");
    }

    @Test
    void redeemableCouponsRespectActiveFlagAndWindow() {
        assertThat(coupons.findRedeemableOn(LocalDate.of(2026, 6, 15))).extracting(CouponEntity::getCode)
                .containsExactly("BIG20", "FREESHIP", "SAVE5", "WELCOME10");
        assertThat(coupons.findRedeemableOn(LocalDate.of(2020, 6, 1))).extracting(CouponEntity::getCode)
                .contains("EXPIRED15");
    }

    @Test
    void conditionalReservationNeverOversells() {
        assertThat(stock.tryReserve("ELE-1008", 1)).isZero();
        assertThat(stock.tryReserve("ELE-1001", 200)).isEqualTo(1);
        assertThat(stock.tryReserve("ELE-1001", 1)).isZero();
        assertThat(stock.findById("ELE-1001")).get().extracting(StockItemEntity::getReserved).isEqualTo(200);
        assertThat(stock.commitReserved("ELE-1002", 1)).isZero();
    }

    @Test
    void lowStockReport() {
        assertThat(stock.findLowStock(3)).extracting(StockItemEntity::getSku).containsExactly("ELE-1008", "TOY-5008");
    }

    @Test
    void orderAggregatesExcludeCancelledOrders() {
        OffsetDateTime t = OffsetDateTime.of(2026, 3, 1, 9, 0, 0, 0, ZoneOffset.UTC);
        save(order("it-o1", "10.00", t), "GRO-2007", 4);
        OrderEntity paid = order("it-o2", "20.00", t.plusMinutes(1));
        paid.transitionTo(OrderStatus.PAID, t.plusMinutes(2));
        save(paid, "GRO-2007", 6);
        OrderEntity cancelled = order("it-o3", "30.00", t.plusMinutes(3));
        cancelled.transitionTo(OrderStatus.CANCELLED, t.plusMinutes(4));
        save(cancelled, "HOM-4001", 9);

        assertThat(orders.lifetimeValue("cus-0005")).isEqualByComparingTo("30.00");
        assertThat(orders.countByStatusForCustomer("cus-0005"))
                .extracting(OrderRepository.StatusCount::getStatus, OrderRepository.StatusCount::getOrders)
                .containsExactlyInAnyOrder(
                        org.assertj.core.groups.Tuple.tuple(OrderStatus.CREATED, 1L),
                        org.assertj.core.groups.Tuple.tuple(OrderStatus.PAID, 1L),
                        org.assertj.core.groups.Tuple.tuple(OrderStatus.CANCELLED, 1L));
        assertThat(orders.unitsSoldBySku()).extracting(OrderRepository.SkuUnits::getSku, OrderRepository.SkuUnits::getUnits)
                .containsExactly(org.assertj.core.groups.Tuple.tuple("GRO-2007", 10L));
        assertThat(orders.findAll(new OrderFilter("cus-0005", OrderStatus.PAID, null, null).toSpecification()))
                .extracting(OrderEntity::getId).containsExactly("it-o2");
        assertThat(orders.findAll(new OrderFilter(null, null, t.plusMinutes(1), t.plusMinutes(3)).toSpecification()))
                .extracting(OrderEntity::getId).containsExactly("it-o2");
    }

    private static OrderEntity order(String id, String total, OffsetDateTime createdAt) {
        BigDecimal amount = new BigDecimal(total);
        BigDecimal zero = new BigDecimal("0.00");
        return new OrderEntity(id, "cus-0005", null, new PriceBreakdown(amount, zero, zero, zero, zero, zero, amount),
                createdAt);
    }

    private void save(OrderEntity order, String sku, int qty) {
        order.addLine(new OrderLineEntity(1, sku, qty, new BigDecimal("1.00"), new BigDecimal(qty).setScale(2)));
        orders.saveAndFlush(order);
    }
}
