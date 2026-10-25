package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.util.Objects;

import org.springframework.stereotype.Component;

import com.retailops.schemas.CustomerTier;

/** Loyalty-tier discount: STANDARD 0%, SILVER 5%, GOLD 10%, PLATINUM 15%. */
@Component
public class TierDiscountPolicy {

    public BigDecimal rate(CustomerTier tier) {
        return switch (Objects.requireNonNull(tier, "tier")) {
            case STANDARD -> new BigDecimal("0.00");
            case SILVER -> new BigDecimal("0.05");
            case GOLD -> new BigDecimal("0.10");
            case PLATINUM -> new BigDecimal("0.15");
        };
    }

    public BigDecimal discount(BigDecimal amount, CustomerTier tier) {
        return Money.percentOf(amount, rate(tier));
    }
}
