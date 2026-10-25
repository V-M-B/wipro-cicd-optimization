package com.retailops.orders.pricing;

import java.util.List;

import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

/** Result of resolving catalog/customer/coupon data and pricing an order. */
public record PricedOrder(String customerId, CustomerTier tier, Region region, List<PricedLine> lines,
        String couponCode, PriceBreakdown breakdown) {

    public PricedOrder {
        lines = List.copyOf(lines);
    }
}
