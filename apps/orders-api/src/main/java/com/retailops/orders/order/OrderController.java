package com.retailops.orders.order;

import java.net.URI;
import java.time.OffsetDateTime;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.retailops.orders.api.PageResponse;
import com.retailops.schemas.Order;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.PriceQuote;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    public static final int MAX_PAGE_SIZE = 100;

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping
    public ResponseEntity<Order> create(@Valid @RequestBody CreateOrderRequest request) {
        Order created = orderService.create(request);
        return ResponseEntity.created(URI.create("/api/orders/" + created.id())).body(created);
    }

    @PostMapping("/quote")
    public PriceQuote quote(@Valid @RequestBody CreateOrderRequest request) {
        return orderService.quote(request);
    }

    @GetMapping("/{id}")
    public Order get(@PathVariable String id) {
        return orderService.get(id);
    }

    @GetMapping
    public PageResponse<Order> list(
            @RequestParam(required = false) String customerId,
            @RequestParam(required = false) OrderStatus status,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime to,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(MAX_PAGE_SIZE) int size) {
        return orderService.list(new OrderFilter(customerId, status, from, to), page, size);
    }

    @PostMapping("/{id}/transitions")
    public Order transition(@PathVariable String id, @Valid @RequestBody StatusTransitionRequest request) {
        return orderService.transition(id, request.target());
    }
}
