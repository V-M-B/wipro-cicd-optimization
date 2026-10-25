package com.retailops.orders.inventory;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;

@ExtendWith(MockitoExtension.class)
class InventoryServiceTest {

    @Mock
    StockRepository repository;

    InventoryService service;

    @BeforeEach
    void setUp() {
        service = new InventoryService(repository);
    }

    private static StockItemEntity item(String sku, int onHand) {
        return new StockItemEntity(sku, onHand);
    }

    @Test
    void reserveSucceedsWhenConditionalUpdateMatches() {
        when(repository.tryReserve("ELE-1001", 3)).thenReturn(1);
        service.reserve("ELE-1001", 3);
        verify(repository, never()).findById(any());
    }

    @Test
    void reserveReportsAvailableStockWhenInsufficient() {
        when(repository.tryReserve("ELE-1001", 30)).thenReturn(0);
        when(repository.findById("ELE-1001")).thenReturn(Optional.of(item("ELE-1001", 12)));
        assertThatThrownBy(() -> service.reserve("ELE-1001", 30))
                .isInstanceOfSatisfying(InsufficientStockException.class, ex -> {
                    assertThat(ex.getSku()).isEqualTo("ELE-1001");
                    assertThat(ex.getRequested()).isEqualTo(30);
                    assertThat(ex.getAvailable()).isEqualTo(12);
                });
    }

    @Test
    void reserveUnknownSkuIsNotFound() {
        when(repository.tryReserve("NOP-0000", 1)).thenReturn(0);
        when(repository.findById("NOP-0000")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.reserve("NOP-0000", 1)).isInstanceOf(NotFoundException.class);
    }

    @ParameterizedTest
    @ValueSource(ints = {0, -1, -50})
    void nonPositiveQuantitiesAreRejectedWithoutTouchingTheDatabase(int qty) {
        assertThatThrownBy(() -> service.reserve("ELE-1001", qty)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> service.release("ELE-1001", qty)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> service.commit("ELE-1001", qty)).isInstanceOf(IllegalArgumentException.class);
        verifyNoInteractions(repository);
    }

    @Test
    void releaseMoreThanReservedFails() {
        when(repository.release("ELE-1001", 5)).thenReturn(0);
        when(repository.findById("ELE-1001")).thenReturn(Optional.of(item("ELE-1001", 10)));
        assertThatThrownBy(() -> service.release("ELE-1001", 5)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void commitWithoutReservationFails() {
        when(repository.commitReserved("ELE-1001", 2)).thenReturn(0);
        when(repository.findById("ELE-1001")).thenReturn(Optional.of(item("ELE-1001", 10)));
        assertThatThrownBy(() -> service.commit("ELE-1001", 2)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void restockReturnsNewLevel() {
        when(repository.restock("ELE-1001", 25)).thenReturn(1);
        when(repository.findById("ELE-1001")).thenReturn(Optional.of(item("ELE-1001", 35)));
        assertThat(service.restock("ELE-1001", 25).onHand()).isEqualTo(35);
    }

    @ParameterizedTest
    @ValueSource(ints = {0, -5, InventoryService.MAX_RESTOCK + 1})
    void restockOutOfRangeIsRejected(int qty) {
        assertThatThrownBy(() -> service.restock("ELE-1001", qty)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void restockUnknownSkuIsNotFound() {
        when(repository.restock("NOP-0000", 1)).thenReturn(0);
        assertThatThrownBy(() -> service.restock("NOP-0000", 1)).isInstanceOf(NotFoundException.class);
    }

    @Test
    void registerRejectsDuplicates() {
        when(repository.existsById("ELE-1001")).thenReturn(true);
        assertThatThrownBy(() -> service.register("ELE-1001", 5)).isInstanceOf(DuplicateResourceException.class);
    }

    @Test
    void registerSavesInitialStock() {
        when(repository.existsById("NEW-0001")).thenReturn(false);
        when(repository.save(any(StockItemEntity.class))).thenAnswer(inv -> inv.getArgument(0));
        StockLevel level = service.register("NEW-0001", 40);
        assertThat(level).isEqualTo(new StockLevel("NEW-0001", 40, 0));
    }

    @Test
    void lowStockMapsEntities() {
        when(repository.findLowStock(5)).thenReturn(List.of(item("ELE-1008", 0), item("TOY-5008", 3)));
        assertThat(service.lowStock(5)).extracting(StockLevel::sku).containsExactly("ELE-1008", "TOY-5008");
        assertThatThrownBy(() -> service.lowStock(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}
