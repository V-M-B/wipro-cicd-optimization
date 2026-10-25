package com.retailops.orders.inventory;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.IntFunction;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.OptimisticLockingFailureException;

import com.retailops.orders.catalog.CreateProductRequest;
import com.retailops.orders.catalog.ProductService;
import com.retailops.orders.customer.CreateCustomerRequest;
import com.retailops.orders.customer.CustomerService;
import com.retailops.orders.order.CreateOrderRequest;
import com.retailops.orders.order.IllegalStatusTransitionException;
import com.retailops.orders.order.OrderLineRequest;
import com.retailops.orders.order.OrderRepository;
import com.retailops.orders.order.OrderService;
import com.retailops.orders.support.PostgresTestcontainersConfig;
import com.retailops.schemas.Category;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.Region;

/** Many threads competing for the same stock rows; PostgreSQL row locks must prevent overselling. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE)
@Import(PostgresTestcontainersConfig.class)
class ConcurrentStockReservationIT {

    private static final AtomicInteger SEQ = new AtomicInteger(1000);
    private static ExecutorService pool;

    @Autowired
    InventoryService inventory;
    @Autowired
    ProductService products;
    @Autowired
    CustomerService customers;
    @Autowired
    OrderService orders;
    @Autowired
    OrderRepository orderRepository;

    @BeforeAll
    static void startPool() {
        pool = Executors.newFixedThreadPool(16);
    }

    @AfterAll
    static void stopPool() {
        pool.shutdownNow();
    }

    private String product(int stock) {
        String sku = "CON-%04d".formatted(SEQ.incrementAndGet());
        products.create(new CreateProductRequest(sku, "Contended " + sku, Category.ELECTRONICS, new BigDecimal("9.99"), stock));
        return sku;
    }

    /** Runs n tasks released at the same instant; returns each task's failure (null = success). */
    private List<Throwable> race(int n, IntFunction<Callable<?>> task) throws Exception {
        CountDownLatch go = new CountDownLatch(1);
        List<Future<?>> futures = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            Callable<?> body = task.apply(i);
            futures.add(pool.submit(() -> {
                go.await();
                return body.call();
            }));
        }
        go.countDown();
        List<Throwable> outcomes = new ArrayList<>();
        for (Future<?> f : futures) {
            try {
                f.get(60, TimeUnit.SECONDS);
                outcomes.add(null);
            } catch (ExecutionException e) {
                outcomes.add(e.getCause());
            }
        }
        return outcomes;
    }

    private static long successes(List<Throwable> outcomes) {
        return outcomes.stream().filter(t -> t == null).count();
    }

    @Test
    void parallelReservationsNeverOversell() throws Exception {
        String sku = product(50);
        List<Throwable> outcomes = race(20, i -> () -> {
            inventory.reserve(sku, 5);
            return null;
        });
        assertThat(successes(outcomes)).isEqualTo(10);
        assertThat(outcomes).filteredOn(t -> t != null).allMatch(t -> t instanceof InsufficientStockException);
        assertThat(inventory.level(sku)).isEqualTo(new StockLevel(sku, 50, 50));
    }

    @Test
    void parallelOrdersRespectStock() throws Exception {
        String sku = product(30);
        String customer = customers.create(new CreateCustomerRequest("Racer", "racer@it.example.com",
                CustomerTier.SILVER, Region.NORTH)).id();
        List<Throwable> outcomes = race(12, i -> () -> orders.create(
                new CreateOrderRequest(customer, List.of(new OrderLineRequest(sku, 3)), null)));
        assertThat(successes(outcomes)).isEqualTo(10);
        assertThat(outcomes).filteredOn(t -> t != null).allMatch(t -> t instanceof InsufficientStockException);
        assertThat(inventory.level(sku).reserved()).isEqualTo(30);
        assertThat(orderRepository.findByCustomerIdOrderByCreatedAtDescIdAsc(customer)).hasSize(10);
    }

    @Test
    void concurrentCancellationReleasesStockExactlyOnce() throws Exception {
        String sku = product(20);
        String customer = customers.create(new CreateCustomerRequest("Canceller", "cancel@it.example.com",
                CustomerTier.GOLD, Region.WEST)).id();
        String orderId = orders.create(new CreateOrderRequest(customer, List.of(new OrderLineRequest(sku, 5)), null)).id();

        List<Throwable> outcomes = race(8, i -> () -> orders.transition(orderId, OrderStatus.CANCELLED));

        assertThat(successes(outcomes)).isEqualTo(1);
        assertThat(outcomes).filteredOn(t -> t != null).allMatch(t -> t instanceof IllegalStatusTransitionException
                || t instanceof OptimisticLockingFailureException);
        assertThat(inventory.level(sku)).isEqualTo(new StockLevel(sku, 20, 0));
        assertThat(orders.get(orderId).status()).isEqualTo(OrderStatus.CANCELLED);
    }

    @Test
    void interleavedReserveAndReleaseKeepCountsConsistent() throws Exception {
        String sku = product(100);
        inventory.reserve(sku, 40);
        List<Throwable> outcomes = race(40, i -> () -> {
            if (i % 2 == 0) {
                inventory.reserve(sku, 1);
            } else {
                inventory.release(sku, 1);
            }
            return null;
        });
        assertThat(successes(outcomes)).isEqualTo(40);
        assertThat(inventory.level(sku)).isEqualTo(new StockLevel(sku, 100, 40));
    }

    @Test
    void parallelRestocksAreAllApplied() throws Exception {
        String sku = product(0);
        List<Throwable> outcomes = race(25, i -> () -> inventory.restock(sku, 4));
        assertThat(successes(outcomes)).isEqualTo(25);
        assertThat(inventory.level(sku).onHand()).isEqualTo(100);
    }
}
