package com.retailops.orders.catalog;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import com.retailops.schemas.Category;

public interface ProductRepository extends JpaRepository<ProductEntity, String> {

    Optional<ProductEntity> findBySku(String sku);

    boolean existsBySku(String sku);

    List<ProductEntity> findBySkuIn(Collection<String> skus);

    List<ProductEntity> findAllByOrderBySkuAsc();

    List<ProductEntity> findByActiveTrueOrderBySkuAsc();

    List<ProductEntity> findByCategoryOrderBySkuAsc(Category category);

    List<ProductEntity> findByCategoryAndActiveTrueOrderBySkuAsc(Category category);

    @Query("select p.category as category, count(p) as products from ProductEntity p "
            + "where p.active = true group by p.category order by p.category")
    List<CategoryCount> countActiveByCategory();

    interface CategoryCount {
        Category getCategory();

        long getProducts();
    }
}
