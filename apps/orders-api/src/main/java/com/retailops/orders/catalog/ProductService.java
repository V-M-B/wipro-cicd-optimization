package com.retailops.orders.catalog;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.inventory.InventoryService;
import com.retailops.orders.pricing.Money;
import com.retailops.orders.validation.SkuValidator;
import com.retailops.schemas.Category;
import com.retailops.schemas.Product;

@Service
public class ProductService {

    private final ProductRepository productRepository;
    private final InventoryService inventoryService;
    private final Clock clock;

    public ProductService(ProductRepository productRepository, InventoryService inventoryService, Clock clock) {
        this.productRepository = productRepository;
        this.inventoryService = inventoryService;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public List<Product> list(Category category, boolean activeOnly) {
        List<ProductEntity> products;
        if (category == null) {
            products = activeOnly ? productRepository.findByActiveTrueOrderBySkuAsc()
                    : productRepository.findAllByOrderBySkuAsc();
        } else {
            products = activeOnly ? productRepository.findByCategoryAndActiveTrueOrderBySkuAsc(category)
                    : productRepository.findByCategoryOrderBySkuAsc(category);
        }
        return products.stream().map(ProductMapper::toDto).toList();
    }

    @Transactional(readOnly = true)
    public Product get(String sku) {
        return ProductMapper.toDto(find(sku));
    }

    @Transactional
    public Product create(CreateProductRequest request) {
        String sku = SkuValidator.normalize(request.sku());
        if (productRepository.existsBySku(sku)) {
            throw new DuplicateResourceException("Product", sku);
        }
        ProductEntity entity = new ProductEntity(UUID.randomUUID().toString(), sku, request.name().trim(),
                request.category(), Money.round(request.unitPrice()), OffsetDateTime.now(clock));
        ProductEntity saved = productRepository.save(entity);
        productRepository.flush();
        inventoryService.register(sku, request.initialStock());
        return ProductMapper.toDto(saved);
    }

    @Transactional
    public Product updatePrice(String sku, BigDecimal newPrice) {
        ProductEntity product = find(sku);
        product.changePrice(Money.round(newPrice));
        return ProductMapper.toDto(product);
    }

    @Transactional
    public Product deactivate(String sku) {
        ProductEntity product = find(sku);
        product.deactivate();
        return ProductMapper.toDto(product);
    }

    private ProductEntity find(String sku) {
        String normalized = SkuValidator.normalize(sku);
        return productRepository.findBySku(normalized)
                .orElseThrow(() -> new NotFoundException("Product", normalized));
    }
}
