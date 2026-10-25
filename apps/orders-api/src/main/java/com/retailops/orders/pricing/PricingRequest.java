package com.retailops.orders.pricing;

import java.time.LocalDate;
import java.util.List;
import java.util.Objects;

import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

/**
 * Input to {@link PricingService}. {@code coupon} and {@code pricingDate} may be null; a null date
 * means "today" according to the service clock.
 */
public record PricingRequest(List<PricedLine> lines, CustomerTier tier, Region region, Coupon coupon,
        LocalDate pricingDate) {

    public PricingRequest {
        lines = lines == null ? List.of() : List.copyOf(lines);
        Objects.requireNonNull(tier, "tier");
        Objects.requireNonNull(region, "region");
    }

    public PricingRequest(List<PricedLine> lines, CustomerTier tier, Region region) {
        this(lines, tier, region, null, null);
    }
}
