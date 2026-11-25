package com.retailops.orders.order;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.SortedMap;
import java.util.UUID;

import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.retailops.orders.api.PageResponse;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.inventory.InventoryService;
import com.retailops.orders.pricing.PricedLine;
import com.retailops.orders.pricing.PricedOrder;
import com.retailops.orders.pricing.QuoteService;
import com.retailops.schemas.Order;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.PriceQuote;

@Service
public class OrderService {

    public static final Sort LIST_SORT = Sort.by(Sort.Order.desc("createdAt"), Sort.Order.asc("id"));

    private final OrderRepository orderRepository;
    private final QuoteService quoteService;
    private final InventoryService inventoryService;
    private final Clock clock;

    public OrderService(OrderRepository orderRepository, QuoteService quoteService,
            InventoryService inventoryService, Clock clock) {
        this.orderRepository = orderRepository;
        this.quoteService = quoteService;
        this.inventoryService = inventoryService;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public PriceQuote quote(CreateOrderRequest request) {
        SortedMap<String, Integer> quantities = OrderLines.consolidate(request.lines());
        return quoteService.price(request.customerId(), quantities, request.couponCode()).breakdown().toPriceQuote();
    }

    /** Prices the order, reserves stock for every line (SKU order, to avoid lock cycles) and saves it. */
    @Transactional
    public Order create(CreateOrderRequest request) {
        SortedMap<String, Integer> quantities = OrderLines.consolidate(request.lines());
        PricedOrder priced = quoteService.price(request.customerId(), quantities, request.couponCode());
        quantities.forEach(inventoryService::reserve);

        OrderEntity order = new OrderEntity(UUID.randomUUID().toString(), priced.customerId(), priced.couponCode(),
                priced.breakdown(), OffsetDateTime.now(clock));
        int lineNo = 1;
        for (PricedLine line : priced.lines()) {
            order.addLine(new OrderLineEntity(lineNo++, line.sku(), line.quantity(), line.unitPrice(),
                    line.lineSubtotal()));
        }
        return OrderMapper.toDto(orderRepository.save(order));
    }

    @Transactional(readOnly = true)
    public Order get(String id) {
        return OrderMapper.toDto(find(id));
    }

    @Transactional(readOnly = true)
    public PageResponse<Order> list(OrderFilter filter, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, LIST_SORT);
        return PageResponse.from(orderRepository.findAll(filter.toSpecification(), pageable), OrderMapper::toDto);
    }

    /**
     * Moves an order through the state machine. Cancelling releases reserved stock; shipping
     * consumes it.
     */
    @Transactional
    public Order transition(String id, OrderStatus target) {
        OrderEntity order = find(id);
        Order before = OrderMapper.toDto(order);
        OrderStatus from = order.transitionTo(target, OffsetDateTime.now(clock));
        if (OrderStateMachine.releasesStock(from, target)) {
            before.lines().forEach(l -> inventoryService.release(l.sku(), l.quantity()));
        } else if (OrderStateMachine.consumesStock(from, target)) {
            before.lines().forEach(l -> inventoryService.commit(l.sku(), l.quantity()));
        }
        return new Order(before.id(), before.customerId(), target, before.lines(), before.couponCode(),
                before.createdAt(), order.getUpdatedAt(), before.total());
    }

    private OrderEntity find(String id) {
        return orderRepository.findById(id).orElseThrow(() -> new NotFoundException("Order", id));
    }
}
