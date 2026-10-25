package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.util.Objects;

import org.springframework.stereotype.Component;

import com.retailops.schemas.Region;

/** Regional sales tax, applied to the discounted merchandise amount (shipping is not taxed). */
@Component
public class TaxPolicy {

    private final PricingProperties properties;

    public TaxPolicy(PricingProperties properties) {
        this.properties = properties;
    }

    public BigDecimal rate(Region region) {
        return properties.taxRates().get(Objects.requireNonNull(region, "region"));
    }

    public BigDecimal tax(BigDecimal taxableAmount, Region region) {
        if (Money.isNegative(taxableAmount)) {
            throw new IllegalArgumentException("taxable amount must not be negative: " + taxableAmount);
        }
        return Money.percentOf(taxableAmount, rate(region));
    }
}
