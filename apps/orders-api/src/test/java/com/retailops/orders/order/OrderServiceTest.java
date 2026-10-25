package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.SortedMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

import com.retailops.orders.api.PageResponse;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.inventory.InsufficientStockException;
import com.retailops.orders.inventory.InventoryService;
import com.retailops.orders.pricing.PriceBreakdown;
import com.retailops.orders.pricing.PricedLine;
import com.retailops.orders.pricing.PricedOrder;
import com.retailops.orders.pricing.QuoteService;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Order;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.Region;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    OrderRepository orderRepository;
    @Mock
    QuoteService quoteService;
    @Mock
    InventoryService inventoryService;

    OrderService service;

    private final PriceBreakdown price = TestFixtures.breakdown("64.97", "0.00", "5.20", "5.99", "76.16");

    @BeforeEach
    void setUp() {
        service = new OrderService(orderRepository, quoteService, inventoryService, TestFixtures.fixedClock());
    }

    private CreateOrderRequest request() {
        return new CreateOrderRequest("cus-1",
                List.of(new OrderLineRequest("TOY-5002", 1), new OrderLineRequest("APP-3001", 3)), null);
    }

    private void stubPricing() {
        when(quoteService.price(eq("cus-1"), any(), isNull())).thenReturn(new PricedOrder("cus-1",
                CustomerTier.STANDARD, Region.NORTH,
                List.of(new PricedLine("APP-3001", 3, new BigDecimal("14.99")),
                        new PricedLine("TOY-5002", 1, new BigDecimal("18.50"))),
                null, price));
    }

    private OrderEntity storedOrder(OrderStatus status) {
        OrderEntity order = new OrderEntity("ord-1", "cus-1", null, price, TestFixtures.NOW_UTC);
        order.addLine(new OrderLineEntity(1, "APP-3001", 3, new BigDecimal("14.99"), new BigDecimal("44.97")));
        order.addLine(new OrderLineEntity(2, "TOY-5002", 1, new BigDecimal("18.50"), new BigDecimal("18.50")));
        if (status == OrderStatus.PAID || status == OrderStatus.SHIPPED) {
            order.transitionTo(OrderStatus.PAID, TestFixtures.NOW_UTC);
        }
        if (status == OrderStatus.SHIPPED) {
            order.transitionTo(OrderStatus.SHIPPED, TestFixtures.NOW_UTC);
        }
        return order;
    }

    @Test
    void createReservesStockInSkuOrderAndSaves() {
        stubPricing();
        when(orderRepository.save(any(OrderEntity.class))).thenAnswer(inv -> inv.getArgument(0));

        Order order = service.create(request());

        InOrder ordered = inOrder(inventoryService, orderRepository);
        ordered.verify(inventoryService).reserve("APP-3001", 3);
        ordered.verify(inventoryService).reserve("TOY-5002", 1);
        ordered.verify(orderRepository).save(any(OrderEntity.class));
        assertThat(order.status()).isEqualTo(OrderStatus.CREATED);
        assertThat(order.total()).isEqualTo(new BigDecimal("76.16"));
        assertThat(order.createdAt()).isEqualTo(TestFixtures.NOW_UTC);
        assertThat(order.lines()).extracting(l -> l.sku()).containsExactly("APP-3001", "TOY-5002");
    }

    @Test
    void createPassesConsolidatedQuantitiesToPricing() {
        stubPricing();
        when(orderRepository.save(any(OrderEntity.class))).thenAnswer(inv -> inv.getArgument(0));
        @SuppressWarnings("unchecked")
        ArgumentCaptor<SortedMap<String, Integer>> captor = ArgumentCaptor.forClass(SortedMap.class);

        service.create(request());

        verify(quoteService).price(eq("cus-1"), captor.capture(), isNull());
        assertThat(captor.getValue()).containsExactlyEntriesOf(
                new java.util.TreeMap<>(java.util.Map.of("APP-3001", 3, "TOY-5002", 1)));
    }

    @Test
    void createStoresLineTotals() {
        stubPricing();
        ArgumentCaptor<OrderEntity> captor = ArgumentCaptor.forClass(OrderEntity.class);
        when(orderRepository.save(captor.capture())).thenAnswer(inv -> inv.getArgument(0));

        service.create(request());

        assertThat(captor.getValue().getLines()).extracting(OrderLineEntity::getLineTotal)
                .containsExactly(new BigDecimal("44.97"), new BigDecimal("18.50"));
        assertThat(captor.getValue().getLines()).extracting(OrderLineEntity::getLineNo).containsExactly(1, 2);
    }

    @Test
    void createDoesNotSaveWhenStockIsInsufficient() {
        stubPricing();
        lenient().doThrow(new InsufficientStockException("TOY-5002", 1, 0)).when(inventoryService).reserve("TOY-5002", 1);

        assertThatThrownBy(() -> service.create(request())).isInstanceOf(InsufficientStockException.class);
        verify(orderRepository, never()).save(any());
    }

    @Test
    void cancellingReleasesEveryLine() {
        when(orderRepository.findById("ord-1")).thenReturn(Optional.of(storedOrder(OrderStatus.PAID)));

        Order order = service.transition("ord-1", OrderStatus.CANCELLED);

        assertThat(order.status()).isEqualTo(OrderStatus.CANCELLED);
        verify(inventoryService).release("APP-3001", 3);
        verify(inventoryService).release("TOY-5002", 1);
        verify(inventoryService, never()).commit(anyString(), anyInt());
    }

    @Test
    void shippingCommitsEveryLine() {
        when(orderRepository.findById("ord-1")).thenReturn(Optional.of(storedOrder(OrderStatus.PAID)));

        service.transition("ord-1", OrderStatus.SHIPPED);

        verify(inventoryService).commit("APP-3001", 3);
        verify(inventoryService).commit("TOY-5002", 1);
        verify(inventoryService, never()).release(anyString(), anyInt());
    }

    @Test
    void payingDoesNotTouchInventory() {
        OrderEntity stored = storedOrder(OrderStatus.CREATED);
        when(orderRepository.findById("ord-1")).thenReturn(Optional.of(stored));

        Order order = service.transition("ord-1", OrderStatus.PAID);

        assertThat(order.status()).isEqualTo(OrderStatus.PAID);
        assertThat(stored.getStatus()).isEqualTo(OrderStatus.PAID);
        verifyNoInteractions(inventoryService);
    }

    @Test
    void illegalTransitionDoesNotTouchInventory() {
        when(orderRepository.findById("ord-1")).thenReturn(Optional.of(storedOrder(OrderStatus.SHIPPED)));

        assertThatThrownBy(() -> service.transition("ord-1", OrderStatus.CANCELLED))
                .isInstanceOf(IllegalStatusTransitionException.class);
        verifyNoInteractions(inventoryService);
    }

    @Test
    void unknownOrderIsNotFound() {
        when(orderRepository.findById("missing")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.get("missing")).isInstanceOf(NotFoundException.class);
        assertThatThrownBy(() -> service.transition("missing", OrderStatus.PAID)).isInstanceOf(NotFoundException.class);
    }

    @Test
    @SuppressWarnings("unchecked")
    void listUsesStableSortAndRequestedPage() {
        ArgumentCaptor<Pageable> pageable = ArgumentCaptor.forClass(Pageable.class);
        when(orderRepository.findAll(any(Specification.class), pageable.capture()))
                .thenAnswer(inv -> new PageImpl<>(List.of(storedOrder(OrderStatus.CREATED)), inv.getArgument(1), 41));

        PageResponse<Order> page = service.list(OrderFilter.none(), 2, 20);

        assertThat(pageable.getValue().getPageNumber()).isEqualTo(2);
        assertThat(pageable.getValue().getPageSize()).isEqualTo(20);
        assertThat(pageable.getValue().getSort()).isEqualTo(OrderService.LIST_SORT);
        assertThat(page.totalElements()).isEqualTo(41);
        assertThat(page.totalPages()).isEqualTo(3);
        assertThat(page.content()).hasSize(1);
    }

    @Test
    void quoteDelegatesToQuoteService() {
        stubPricing();
        assertThat(service.quote(request()).total()).isEqualTo(new BigDecimal("76.16"));
        verifyNoInteractions(inventoryService, orderRepository);
    }
}
