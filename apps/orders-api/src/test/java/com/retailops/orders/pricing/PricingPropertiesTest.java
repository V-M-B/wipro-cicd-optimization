package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.retailops.schemas.Region;

class PricingPropertiesTest {

    @Test
    void defaultsAreComplete() {
        PricingProperties p = PricingProperties.defaults();
        assertThat(p.freeShippingThreshold()).isEqualByComparingTo("75.00");
        assertThat(p.perUnitShippingSurcharge()).isEqualByComparingTo("0.50");
        assertThat(p.surchargeFreeUnits()).isEqualTo(5);
        assertThat(p.taxRates()).containsOnlyKeys(Region.values());
        assertThat(p.shippingBaseRates()).containsOnlyKeys(Region.values());
    }

    @Test
    void partialRegionOverridesAreMergedOverDefaults() {
        PricingProperties p = new PricingProperties(null, Map.of(Region.EAST, new BigDecimal("0.05")),
                Map.of(Region.NORTH, new BigDecimal("1.00")), null, null);
        assertThat(p.taxRates().get(Region.EAST)).isEqualByComparingTo("0.05");
        assertThat(p.taxRates().get(Region.WEST)).isEqualByComparingTo("0.09");
        assertThat(p.shippingBaseRates().get(Region.NORTH)).isEqualByComparingTo("1.00");
        assertThat(p.shippingBaseRates().get(Region.SOUTH)).isEqualByComparingTo("4.99");
    }

    @Test
    void mapsAreImmutable() {
        PricingProperties p = PricingProperties.defaults();
        assertThatThrownBy(() -> p.taxRates().put(Region.EAST, BigDecimal.ONE))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void negativeThresholdIsRejected() {
        assertThatThrownBy(() -> new PricingProperties(new BigDecimal("-1"), null, null, null, null))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
