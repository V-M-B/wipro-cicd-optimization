package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;

import org.springframework.boot.context.properties.ConfigurationProperties;

import com.retailops.schemas.Region;

/**
 * Configurable pricing parameters ({@code orders.pricing.*}). Any value left unset falls back to
 * the defaults below; region maps are merged over the defaults.
 */
@ConfigurationProperties(prefix = "orders.pricing")
public record PricingProperties(
        BigDecimal freeShippingThreshold,
        Map<Region, BigDecimal> taxRates,
        Map<Region, BigDecimal> shippingBaseRates,
        BigDecimal perUnitShippingSurcharge,
        Integer surchargeFreeUnits) {

    public static final BigDecimal DEFAULT_FREE_SHIPPING_THRESHOLD = new BigDecimal("75.00");
    public static final BigDecimal DEFAULT_PER_UNIT_SURCHARGE = new BigDecimal("0.50");
    public static final int DEFAULT_SURCHARGE_FREE_UNITS = 5;

    public static final Map<Region, BigDecimal> DEFAULT_TAX_RATES = Collections.unmodifiableMap(new EnumMap<>(Map.of(
            Region.NORTH, new BigDecimal("0.0800"),
            Region.SOUTH, new BigDecimal("0.0650"),
            Region.EAST, new BigDecimal("0.0725"),
            Region.WEST, new BigDecimal("0.0900"))));

    public static final Map<Region, BigDecimal> DEFAULT_SHIPPING_BASE_RATES = Collections.unmodifiableMap(new EnumMap<>(Map.of(
            Region.NORTH, new BigDecimal("5.99"),
            Region.SOUTH, new BigDecimal("4.99"),
            Region.EAST, new BigDecimal("5.49"),
            Region.WEST, new BigDecimal("6.99"))));

    public PricingProperties {
        freeShippingThreshold = freeShippingThreshold == null ? DEFAULT_FREE_SHIPPING_THRESHOLD : freeShippingThreshold;
        perUnitShippingSurcharge = perUnitShippingSurcharge == null ? DEFAULT_PER_UNIT_SURCHARGE : perUnitShippingSurcharge;
        surchargeFreeUnits = surchargeFreeUnits == null ? DEFAULT_SURCHARGE_FREE_UNITS : surchargeFreeUnits;
        taxRates = merge(DEFAULT_TAX_RATES, taxRates);
        shippingBaseRates = merge(DEFAULT_SHIPPING_BASE_RATES, shippingBaseRates);
        if (freeShippingThreshold.signum() < 0 || perUnitShippingSurcharge.signum() < 0 || surchargeFreeUnits < 0) {
            throw new IllegalArgumentException("pricing properties must not be negative");
        }
    }

    public static PricingProperties defaults() {
        return new PricingProperties(null, null, null, null, null);
    }

    private static Map<Region, BigDecimal> merge(Map<Region, BigDecimal> defaults, Map<Region, BigDecimal> overrides) {
        EnumMap<Region, BigDecimal> merged = new EnumMap<>(defaults);
        if (overrides != null) {
            merged.putAll(overrides);
        }
        return Collections.unmodifiableMap(merged);
    }
}
