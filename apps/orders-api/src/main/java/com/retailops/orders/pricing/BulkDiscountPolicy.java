package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.util.List;

import org.springframework.stereotype.Component;

/**
 * Per-line quantity discount: 10+ units 2%, 20+ 5%, 50+ 8%, 100+ 12%.
 */
@Component
public class BulkDiscountPolicy {

    record Tier(int minQuantity, BigDecimal rate) {
    }

    static final List<Tier> TIERS = List.of(
            new Tier(100, new BigDecimal("0.12")),
            new Tier(50, new BigDecimal("0.08")),
            new Tier(20, new BigDecimal("0.05")),
            new Tier(10, new BigDecimal("0.02")));

    public BigDecimal rate(int quantity) {
        if (quantity < 0) {
            throw new IllegalArgumentException("quantity must not be negative: " + quantity);
        }
        for (Tier tier : TIERS) {
            if (quantity >= tier.minQuantity()) {
                return tier.rate();
            }
        }
        return new BigDecimal("0.00");
    }

    public BigDecimal discount(BigDecimal lineSubtotal, int quantity) {
        return Money.percentOf(lineSubtotal, rate(quantity));
    }
}
