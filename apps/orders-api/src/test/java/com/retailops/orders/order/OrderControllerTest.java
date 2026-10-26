package com.retailops.orders.order;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Set;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import com.retailops.orders.api.GlobalExceptionHandler;
import com.retailops.orders.api.PageResponse;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.inventory.InsufficientStockException;
import com.retailops.orders.pricing.CouponRejectedException;
import com.retailops.orders.pricing.CouponRejectionReason;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.Order;
import com.retailops.schemas.OrderLine;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.PriceQuote;

@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired
    MockMvc mvc;

    @MockitoBean
    OrderService orderService;

    private static final String BODY = """
            {"customerId":"cus-0001","lines":[{"sku":"ELE-1001","quantity":2}]}""";

    private Order order(OrderStatus status) {
        return new Order("ord-1", "cus-0001", status,
                List.of(new OrderLine("ELE-1001", 2, new BigDecimal("24.99"), new BigDecimal("49.98"))),
                null, TestFixtures.NOW_UTC, new BigDecimal("59.97"));
    }

    @Test
    void createReturns201WithLocation() throws Exception {
        when(orderService.create(any())).thenReturn(order(OrderStatus.CREATED));
        mvc.perform(post("/api/orders").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/orders/ord-1"))
                .andExpect(jsonPath("$.status").value("CREATED"))
                .andExpect(jsonPath("$.total").value(59.97));
    }

    @Test
    void createWithoutLinesIsRejected() throws Exception {
        mvc.perform(post("/api/orders").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"customerId\":\"cus-0001\",\"lines\":[]}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("lines"));
        verifyNoInteractions(orderService);
    }

    @Test
    void createWithZeroQuantityReportsLinePath() throws Exception {
        mvc.perform(post("/api/orders").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"customerId\":\"cus-0001\",\"lines\":[{\"sku\":\"ELE-1001\",\"quantity\":0}]}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("lines[0].quantity"));
    }

    @Test
    void insufficientStockIsConflict() throws Exception {
        when(orderService.create(any())).thenThrow(new InsufficientStockException("ELE-1001", 2, 1));
        mvc.perform(post("/api/orders").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value(GlobalExceptionHandler.TYPE_BASE + "insufficient-stock"))
                .andExpect(jsonPath("$.sku").value("ELE-1001"))
                .andExpect(jsonPath("$.available").value(1));
    }

    @Test
    void rejectedCouponIsUnprocessable() throws Exception {
        when(orderService.create(any())).thenThrow(new CouponRejectedException("EXPIRED15", CouponRejectionReason.EXPIRED));
        mvc.perform(post("/api/orders").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.type").value(GlobalExceptionHandler.TYPE_BASE + "coupon-rejected"))
                .andExpect(jsonPath("$.reason").value("EXPIRED"));
    }

    @Test
    void unknownCustomerIs404() throws Exception {
        when(orderService.create(any())).thenThrow(new NotFoundException("Customer", "cus-0001"));
        mvc.perform(post("/api/orders").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isNotFound());
    }

    @Test
    void getReturnsOrder() throws Exception {
        when(orderService.get("ord-1")).thenReturn(order(OrderStatus.PAID));
        mvc.perform(get("/api/orders/ord-1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PAID"))
                .andExpect(jsonPath("$.createdAt").value("2026-06-15T10:00:00Z"))
                .andExpect(jsonPath("$.lines[0].unitPrice").value(24.99));
    }

    @Test
    void listUsesDefaultPaging() throws Exception {
        when(orderService.list(any(), anyInt(), anyInt())).thenReturn(new PageResponse<>(List.of(), 0, 20, 0, 0));
        mvc.perform(get("/api/orders")).andExpect(status().isOk()).andExpect(jsonPath("$.size").value(20));
        verify(orderService).list(OrderFilter.none(), 0, 20);
    }

    @Test
    void listParsesFilters() throws Exception {
        when(orderService.list(any(), anyInt(), anyInt())).thenReturn(new PageResponse<>(List.of(), 2, 5, 0, 0));
        mvc.perform(get("/api/orders").param("customerId", "cus-0001").param("status", "PAID")
                        .param("from", "2026-01-01T00:00:00Z").param("to", "2026-02-01T00:00:00Z")
                        .param("page", "2").param("size", "5"))
                .andExpect(status().isOk());
        verify(orderService).list(eq(new OrderFilter("cus-0001", OrderStatus.PAID,
                OffsetDateTime.parse("2026-01-01T00:00:00Z"), OffsetDateTime.parse("2026-02-01T00:00:00Z"))), eq(2), eq(5));
    }

    @Test
    void pageSizeAboveMaximumIsRejected() throws Exception {
        mvc.perform(get("/api/orders").param("size", "101"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("size"));
        verifyNoInteractions(orderService);
    }

    @Test
    void negativePageIsRejected() throws Exception {
        mvc.perform(get("/api/orders").param("page", "-1")).andExpect(status().isBadRequest());
        verifyNoInteractions(orderService);
    }

    @Test
    void invertedDateRangeIsUnprocessable() throws Exception {
        mvc.perform(get("/api/orders").param("from", "2026-02-01T00:00:00Z").param("to", "2026-01-01T00:00:00Z"))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("INVALID_DATE_RANGE"));
    }

    @Test
    void transitionReturnsUpdatedOrder() throws Exception {
        when(orderService.transition("ord-1", OrderStatus.PAID)).thenReturn(order(OrderStatus.PAID));
        mvc.perform(post("/api/orders/ord-1/transitions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"target\":\"PAID\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PAID"));
    }

    @Test
    void illegalTransitionIsConflictWithAllowedTargets() throws Exception {
        when(orderService.transition("ord-1", OrderStatus.CANCELLED)).thenThrow(
                new IllegalStatusTransitionException(OrderStatus.SHIPPED, OrderStatus.CANCELLED, Set.of(OrderStatus.DELIVERED)));
        mvc.perform(post("/api/orders/ord-1/transitions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"target\":\"CANCELLED\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.from").value("SHIPPED"))
                .andExpect(jsonPath("$.allowed[0]").value("DELIVERED"));
    }

    @Test
    void transitionWithoutTargetIsRejected() throws Exception {
        mvc.perform(post("/api/orders/ord-1/transitions").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(orderService);
    }

    @Test
    void concurrentModificationIsConflict() throws Exception {
        when(orderService.transition("ord-1", OrderStatus.PAID))
                .thenThrow(new ObjectOptimisticLockingFailureException(OrderEntity.class, "ord-1"));
        mvc.perform(post("/api/orders/ord-1/transitions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"target\":\"PAID\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value(GlobalExceptionHandler.TYPE_BASE + "concurrent-modification"));
    }

    @Test
    void quoteReturnsBreakdown() throws Exception {
        when(orderService.quote(any())).thenReturn(new PriceQuote(new BigDecimal("49.98"), new BigDecimal("0.00"),
                new BigDecimal("4.00"), new BigDecimal("5.99"), new BigDecimal("59.97")));
        mvc.perform(post("/api/orders/quote").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.subtotal").value(49.98))
                .andExpect(jsonPath("$.shipping").value(5.99))
                .andExpect(jsonPath("$.total").value(59.97));
    }
}
