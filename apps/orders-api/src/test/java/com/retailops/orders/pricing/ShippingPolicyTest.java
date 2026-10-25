package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

class ShippingPolicyTest {

    private final ShippingPolicy policy = new ShippingPolicy(PricingProperties.defaults());

    @Test
    void freeAtExactlyTheThreshold() {
        assertThat(policy.cost(new BigDecimal("75.00"), 3, Region.NORTH, CustomerTier.STANDARD, false))
                .isEqualTo(Money.ZERO);
    }

    @Test
    void chargedJustBelowTheThreshold() {
        assertThat(policy.cost(new BigDecimal("74.99"), 3, Region.NORTH, CustomerTier.STANDARD, false))
                .isEqualTo(new BigDecimal("5.99"));
    }

    @ParameterizedTest
    @EnumSource(Region.class)
    void platinumAlwaysShipsFree(Region region) {
        assertThat(policy.cost(new BigDecimal("1.00"), 40, region, CustomerTier.PLATINUM, false))
                .isEqualTo(Money.ZERO);
    }

    @Test
    void freeShippingCouponWaivesCharge() {
        assertThat(policy.cost(new BigDecimal("10.00"), 12, Region.WEST, CustomerTier.SILVER, true))
                .isEqualTo(Money.ZERO);
    }

    @Test
    void surchargeAppliesPerUnitBeyondFive() {
        // 5.99 base + 3 surcharged units x 0.50
        assertThat(policy.cost(new BigDecimal("40.00"), 8, Region.NORTH, CustomerTier.GOLD, false))
                .isEqualTo(new BigDecimal("7.49"));
    }

    @Test
    void customThresholdAndSurchargeAreHonoured() {
        ShippingPolicy custom = new ShippingPolicy(new PricingProperties(new BigDecimal("200.00"), null, null,
                new BigDecimal("1.00"), 2));
        assertThat(custom.cost(new BigDecimal("150.00"), 4, Region.SOUTH, CustomerTier.STANDARD, false))
                .isEqualTo(new BigDecimal("6.99"));
        assertThat(custom.qualifiesForFreeShipping(new BigDecimal("200.00"), CustomerTier.STANDARD, false)).isTrue();
    }

    @Test
    void zeroUnitsIsRejected() {
        assertThatThrownBy(() -> policy.cost(new BigDecimal("10.00"), 0, Region.EAST, CustomerTier.STANDARD, false))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
