package com.retailops.orders.catalog;

import java.net.URI;
import java.util.List;

import jakarta.validation.Valid;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.retailops.schemas.Category;
import com.retailops.schemas.Product;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping
    public List<Product> list(@RequestParam(required = false) Category category,
            @RequestParam(defaultValue = "false") boolean activeOnly) {
        return productService.list(category, activeOnly);
    }

    @GetMapping("/{sku}")
    public Product get(@PathVariable String sku) {
        return productService.get(sku);
    }

    @PostMapping
    public ResponseEntity<Product> create(@Valid @RequestBody CreateProductRequest request) {
        Product created = productService.create(request);
        return ResponseEntity.created(URI.create("/api/products/" + created.sku())).body(created);
    }

    @PutMapping("/{sku}/price")
    public Product updatePrice(@PathVariable String sku, @Valid @RequestBody PriceUpdateRequest request) {
        return productService.updatePrice(sku, request.unitPrice());
    }

    @PostMapping("/{sku}/deactivate")
    public Product deactivate(@PathVariable String sku) {
        return productService.deactivate(sku);
    }
}
