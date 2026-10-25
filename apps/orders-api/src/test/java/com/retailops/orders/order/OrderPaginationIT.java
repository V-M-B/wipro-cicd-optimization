package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.retailops.orders.catalog.CreateProductRequest;
import com.retailops.orders.catalog.ProductService;
import com.retailops.orders.customer.CreateCustomerRequest;
import com.retailops.orders.customer.CustomerService;
import com.retailops.orders.support.PostgresTestcontainersConfig;
import com.retailops.schemas.Category;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Order;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.Region;

/**
 * Pagination and filtering through MockMvc against PostgreSQL. Uses its own context (mock web
 * environment + a deterministic stepping clock) so creation timestamps are strictly increasing.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({PostgresTestcontainersConfig.class, OrderPaginationIT.SteppingClockConfig.class})
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class OrderPaginationIT {

    static final int ORDER_COUNT = 23;

    @TestConfiguration(proxyBeanMethods = false)
    static class SteppingClockConfig {
        @Bean
        @Primary
        Clock steppingClock() {
            return new SteppingClock(Instant.parse("2026-03-01T09:00:00Z"));
        }
    }

    /** Advances one second on every read: deterministic, strictly increasing timestamps. */
    static final class SteppingClock extends Clock {
        private final Instant start;
        private final AtomicLong ticks = new AtomicLong();

        SteppingClock(Instant start) {
            this.start = start;
        }

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return start.plusSeconds(ticks.getAndIncrement());
        }
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    ObjectMapper json;
    @Autowired
    OrderService orderService;
    @Autowired
    ProductService productService;
    @Autowired
    CustomerService customerService;

    String customerId;
    final List<Order> created = new ArrayList<>();

    @BeforeAll
    void createOrders() {
        customerId = customerService.create(new CreateCustomerRequest("Paging Customer", "paging@it.example.com",
                CustomerTier.STANDARD, Region.EAST)).id();
        productService.create(new CreateProductRequest("PAG-1001", "Paging widget", Category.HOME,
                new BigDecimal("4.00"), 10_000));
        for (int i = 0; i < ORDER_COUNT; i++) {
            Order order = orderService.create(new CreateOrderRequest(customerId,
                    List.of(new OrderLineRequest("PAG-1001", 1 + i % 4)), null));
            if (i % 3 == 0) {
                order = orderService.transition(order.id(), OrderStatus.PAID);
            } else if (i % 5 == 4) {
                order = orderService.transition(order.id(), OrderStatus.CANCELLED);
            }
            created.add(order);
        }
    }

    private JsonNode page(MockHttpServletRequestBuilder request) throws Exception {
        String body = mvc.perform(request.param("customerId", customerId)).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(body);
    }

    private static List<String> ids(JsonNode page) {
        List<String> ids = new ArrayList<>();
        page.get("content").forEach(o -> ids.add(o.get("id").asText()));
        return ids;
    }

    private List<String> newestFirst() {
        List<String> ids = new ArrayList<>(created.stream().map(Order::id).toList());
        Collections.reverse(ids);
        return ids;
    }

    @Test
    void firstPageIsNewestFirst() throws Exception {
        JsonNode first = page(get("/api/orders").param("size", "10"));
        assertThat(first.get("totalElements").asLong()).isEqualTo(ORDER_COUNT);
        assertThat(first.get("totalPages").asInt()).isEqualTo(3);
        assertThat(ids(first)).isEqualTo(newestFirst().subList(0, 10));
    }

    @Test
    void lastPageHoldsTheRemainder() throws Exception {
        JsonNode last = page(get("/api/orders").param("size", "10").param("page", "2"));
        assertThat(ids(last)).containsExactlyElementsOf(newestFirst().subList(20, 23));
    }

    @Test
    void pageBeyondTheEndIsEmpty() throws Exception {
        JsonNode beyond = page(get("/api/orders").param("size", "10").param("page", "5"));
        assertThat(beyond.get("content")).isEmpty();
        assertThat(beyond.get("totalElements").asLong()).isEqualTo(ORDER_COUNT);
    }

    @Test
    void pagesPartitionAllOrdersWithoutGapsOrDuplicates() throws Exception {
        List<String> seen = new ArrayList<>();
        for (int p = 0; p < 4; p++) {
            seen.addAll(ids(page(get("/api/orders").param("size", "7").param("page", String.valueOf(p)))));
        }
        assertThat(seen).isEqualTo(newestFirst());
    }

    @Test
    void statusFilterCountsMatch() throws Exception {
        long paid = created.stream().filter(o -> o.status() == OrderStatus.PAID).count();
        long cancelled = created.stream().filter(o -> o.status() == OrderStatus.CANCELLED).count();
        assertThat(paid).isEqualTo(8);
        assertThat(cancelled).isEqualTo(3);
        assertThat(page(get("/api/orders").param("status", "PAID")).get("totalElements").asLong()).isEqualTo(paid);
        assertThat(page(get("/api/orders").param("status", "CANCELLED")).get("totalElements").asLong()).isEqualTo(cancelled);
    }

    @Test
    void createdAtRangeIsInclusiveExclusive() throws Exception {
        OffsetDateTime from = created.get(5).createdAt();
        OffsetDateTime to = created.get(15).createdAt();
        JsonNode range = page(get("/api/orders").param("from", from.toString()).param("to", to.toString())
                .param("size", "50"));
        assertThat(range.get("totalElements").asLong()).isEqualTo(10);
        assertThat(ids(range)).containsExactlyInAnyOrderElementsOf(created.subList(5, 15).stream().map(Order::id).toList());
    }

    @Test
    void oversizedPageIsRejected() throws Exception {
        mvc.perform(get("/api/orders").param("size", "500")).andExpect(status().isBadRequest());
    }
}
