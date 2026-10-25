package com.retailops.orders.support;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import com.retailops.orders.pricing.PriceBreakdown;
import com.retailops.orders.pricing.PricingProperties;
import com.retailops.orders.pricing.PricingService;

/** Shared deterministic fixtures for unit tests. */
public final class TestFixtures {

    public static final LocalDate PRICING_DATE = LocalDate.of(2026, 6, 15);
    public static final Instant NOW = Instant.parse("2026-06-15T10:00:00Z");
    public static final OffsetDateTime NOW_UTC = OffsetDateTime.ofInstant(NOW, ZoneOffset.UTC);

    private TestFixtures() {
    }

    public static Clock fixedClock() {
        return Clock.fixed(NOW, ZoneOffset.UTC);
    }

    public static PricingService defaultPricingService() {
        return PricingService.withDefaults(PricingProperties.defaults(), fixedClock());
    }

    public static BigDecimal money(String amount) {
        return new BigDecimal(amount);
    }

    public static PriceBreakdown breakdown(String subtotal, String discount, String tax, String shipping,
            String total) {
        return new PriceBreakdown(money(subtotal), money(discount), money("0.00"), money("0.00"), money(tax),
                money(shipping), money(total));
    }
}
