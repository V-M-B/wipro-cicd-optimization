package com.retailops.orders.catalog;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.inventory.InventoryService;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.Category;
import com.retailops.schemas.Product;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    @Mock
    ProductRepository repository;
    @Mock
    InventoryService inventoryService;

    ProductService service;

    @BeforeEach
    void setUp() {
        service = new ProductService(repository, inventoryService, TestFixtures.fixedClock());
    }

    private static ProductEntity entity(String sku, Category category, String price) {
        return new ProductEntity("id-" + sku, sku, "Item " + sku, category, new BigDecimal(price), TestFixtures.NOW_UTC);
    }

    @ParameterizedTest(name = "category={0} activeOnly={1}")
    @CsvSource({", false", ", true", "TOYS, false", "TOYS, true"})
    void listChoosesQueryByFilters(Category category, boolean activeOnly) {
        List<ProductEntity> result = List.of(entity("TOY-5001", Category.TOYS, "44.99"));
        if (category == null && !activeOnly) {
            when(repository.findAllByOrderBySkuAsc()).thenReturn(result);
        } else if (category == null) {
            when(repository.findByActiveTrueOrderBySkuAsc()).thenReturn(result);
        } else if (!activeOnly) {
            when(repository.findByCategoryOrderBySkuAsc(category)).thenReturn(result);
        } else {
            when(repository.findByCategoryAndActiveTrueOrderBySkuAsc(category)).thenReturn(result);
        }
        assertThat(service.list(category, activeOnly)).extracting(Product::sku).containsExactly("TOY-5001");
    }

    @Test
    void getNormalisesSku() {
        when(repository.findBySku("ELE-1001")).thenReturn(Optional.of(entity("ELE-1001", Category.ELECTRONICS, "24.99")));
        assertThat(service.get(" ele-1001 ").unitPrice()).isEqualTo(new BigDecimal("24.99"));
    }

    @Test
    void getMissingIsNotFound() {
        when(repository.findBySku("NOP-0001")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.get("nop-0001"))
                .isInstanceOfSatisfying(NotFoundException.class,
                        ex -> assertThat(ex.getIdentifier()).isEqualTo("NOP-0001"));
    }

    @Test
    void createRejectsDuplicateSku() {
        when(repository.existsBySku("HOM-4001")).thenReturn(true);
        assertThatThrownBy(() -> service.create(new CreateProductRequest("hom-4001", "Mug", Category.HOME,
                new BigDecimal("6.99"), 10))).isInstanceOf(DuplicateResourceException.class);
        verify(repository, never()).save(any());
    }

    @Test
    void createSavesNormalisedProductAndRegistersStock() {
        when(repository.existsBySku("HOM-4999")).thenReturn(false);
        ArgumentCaptor<ProductEntity> saved = ArgumentCaptor.forClass(ProductEntity.class);
        when(repository.save(saved.capture())).thenAnswer(inv -> inv.getArgument(0));

        Product product = service.create(new CreateProductRequest("HOM-4999", "  Lamp  ", Category.HOME,
                new BigDecimal("27.7"), 15));

        assertThat(product.sku()).isEqualTo("HOM-4999");
        assertThat(product.name()).isEqualTo("Lamp");
        assertThat(product.unitPrice()).isEqualTo(new BigDecimal("27.70"));
        assertThat(product.active()).isTrue();
        assertThat(saved.getValue().getCreatedAt()).isEqualTo(TestFixtures.NOW_UTC);
        verify(inventoryService).register("HOM-4999", 15);
    }

    @Test
    void updatePriceRoundsHalfEven() {
        when(repository.findBySku("ELE-1001")).thenReturn(Optional.of(entity("ELE-1001", Category.ELECTRONICS, "24.99")));
        assertThat(service.updatePrice("ELE-1001", new BigDecimal("10.005")).unitPrice())
                .isEqualTo(new BigDecimal("10.00"));
    }

    @Test
    void deactivateClearsActiveFlag() {
        when(repository.findBySku("TOY-5001")).thenReturn(Optional.of(entity("TOY-5001", Category.TOYS, "44.99")));
        assertThat(service.deactivate("TOY-5001").active()).isFalse();
    }

    @Test
    void entityRejectsNonPositivePrice() {
        ProductEntity product = entity("TOY-5001", Category.TOYS, "44.99");
        assertThatThrownBy(() -> product.changePrice(BigDecimal.ZERO)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> product.changePrice(null)).isInstanceOf(IllegalArgumentException.class);
    }
}
