package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.util.Objects;

import org.springframework.stereotype.Component;

import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

/**
 * Shipping: free when the discounted merchandise amount reaches the threshold, for PLATINUM
 * customers, or with a free-shipping coupon. Otherwise the regional base rate plus a per-unit
 * surcharge for every unit beyond the first {@code surchargeFreeUnits}.
 */
@Component
public class ShippingPolicy {

    private final PricingProperties properties;

    public ShippingPolicy(PricingProperties properties) {
        this.properties = properties;
    }

    public boolean qualifiesForFreeShipping(BigDecimal netMerchandise, CustomerTier tier, boolean freeShippingCoupon) {
        return freeShippingCoupon
                || tier == CustomerTier.PLATINUM
                || netMerchandise.compareTo(properties.freeShippingThreshold()) >= 0;
    }

    public BigDecimal cost(BigDecimal netMerchandise, int units, Region region, CustomerTier tier,
            boolean freeShippingCoupon) {
        Objects.requireNonNull(netMerchandise, "netMerchandise");
        Objects.requireNonNull(region, "region");
        if (units <= 0) {
            throw new IllegalArgumentException("units must be positive: " + units);
        }
        if (qualifiesForFreeShipping(netMerchandise, tier, freeShippingCoupon)) {
            return Money.ZERO;
        }
        int surchargedUnits = Math.max(0, units - properties.surchargeFreeUnits());
        BigDecimal surcharge = properties.perUnitShippingSurcharge().multiply(BigDecimal.valueOf(surchargedUnits));
        return Money.round(properties.shippingBaseRates().get(region).add(surcharge));
    }
}
