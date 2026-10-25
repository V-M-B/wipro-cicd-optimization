package com.retailops.orders.pricing;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.SortedMap;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.retailops.orders.catalog.ProductEntity;
import com.retailops.orders.catalog.ProductRepository;
import com.retailops.orders.common.BusinessRuleException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.customer.CustomerEntity;
import com.retailops.orders.customer.CustomerRepository;

/** Resolves customer, catalog prices and coupon from the database, then prices the order. */
@Service
public class QuoteService {

    private final CustomerRepository customerRepository;
    private final ProductRepository productRepository;
    private final CouponRepository couponRepository;
    private final PricingService pricingService;

    public QuoteService(CustomerRepository customerRepository, ProductRepository productRepository,
            CouponRepository couponRepository, PricingService pricingService) {
        this.customerRepository = customerRepository;
        this.productRepository = productRepository;
        this.couponRepository = couponRepository;
        this.pricingService = pricingService;
    }

    /**
     * @param quantitiesBySku consolidated, SKU-sorted quantities
     */
    @Transactional(readOnly = true)
    public PricedOrder price(String customerId, SortedMap<String, Integer> quantitiesBySku, String couponCode) {
        CustomerEntity customer = customerRepository.findById(customerId)
                .orElseThrow(() -> new NotFoundException("Customer", customerId));
        if (quantitiesBySku.isEmpty()) {
            throw new BusinessRuleException("EMPTY_ORDER", "An order needs at least one line");
        }
        Map<String, ProductEntity> products = productRepository.findBySkuIn(quantitiesBySku.keySet()).stream()
                .collect(Collectors.toMap(ProductEntity::getSku, Function.identity()));

        List<PricedLine> lines = new ArrayList<>();
        for (Map.Entry<String, Integer> entry : quantitiesBySku.entrySet()) {
            ProductEntity product = products.get(entry.getKey());
            if (product == null) {
                throw new NotFoundException("Product", entry.getKey());
            }
            if (!product.isActive()) {
                throw new BusinessRuleException("PRODUCT_INACTIVE",
                        "Product '" + product.getSku() + "' is no longer sold");
            }
            lines.add(new PricedLine(product.getSku(), entry.getValue(), product.getUnitPrice()));
        }

        Coupon coupon = resolveCoupon(couponCode);
        PriceBreakdown breakdown = pricingService.quote(
                new PricingRequest(lines, customer.getTier(), customer.getRegion(), coupon, null));
        return new PricedOrder(customer.getId(), customer.getTier(), customer.getRegion(), lines,
                coupon == null ? null : coupon.code(), breakdown);
    }

    Coupon resolveCoupon(String couponCode) {
        if (couponCode == null || couponCode.isBlank()) {
            return null;
        }
        String normalized = couponCode.trim().toUpperCase(Locale.ROOT);
        return couponRepository.findById(normalized)
                .map(CouponEntity::toCoupon)
                .orElseThrow(() -> new CouponRejectedException(normalized, CouponRejectionReason.UNKNOWN));
    }
}
