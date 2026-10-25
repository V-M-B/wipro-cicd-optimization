package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

import com.retailops.orders.order.CreateOrderRequest;
import com.retailops.orders.order.OrderLineRequest;
import com.retailops.orders.order.OrderService;
import com.retailops.orders.support.PostgresTestcontainersConfig;
import com.retailops.schemas.PriceQuote;
import com.retailops.schemas.Region;

/**
 * Pricing with overridden configuration properties (its own Spring context and database), using
 * seeded customers, products and coupons.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE, properties = {
        "orders.pricing.free-shipping-threshold=500.00",
        "orders.pricing.tax-rates.WEST=0.1000",
        "orders.pricing.shipping-base-rates.NORTH=9.99"})
@Import(PostgresTestcontainersConfig.class)
class PricingConfigurationIT {

    @Autowired
    PricingProperties properties;
    @Autowired
    OrderService orderService;

    private PriceQuote quote(String customer, String coupon, String sku, int qty) {
        return orderService.quote(new CreateOrderRequest(customer, List.of(new OrderLineRequest(sku, qty)), coupon));
    }

    @Test
    void propertiesAreBoundAndMergedWithDefaults() {
        assertThat(properties.freeShippingThreshold()).isEqualByComparingTo("500.00");
        assertThat(properties.taxRates().get(Region.WEST)).isEqualByComparingTo("0.1000");
        assertThat(properties.taxRates().get(Region.NORTH)).isEqualByComparingTo("0.0800");
        assertThat(properties.shippingBaseRates().get(Region.NORTH)).isEqualByComparingTo("9.99");
        assertThat(properties.shippingBaseRates().get(Region.WEST)).isEqualByComparingTo("6.99");
    }

    @Test
    void westTaxOverrideAndRaisedThreshold() {
        // cus-0012 STANDARD/WEST, 2 x ELE-1002 @ 89.50
        PriceQuote q = quote("cus-0012", null, "ELE-1002", 2);
        assertThat(q.subtotal()).isEqualByComparingTo("179.00");
        assertThat(q.tax()).isEqualByComparingTo("17.90");
        assertThat(q.shipping()).isEqualByComparingTo("6.99");
        assertThat(q.total()).isEqualByComparingTo("203.89");
    }

    @Test
    void northShippingOverride() {
        // cus-0001 STANDARD/NORTH, 1 x APP-3003 @ 79.00 (would ship free under the default threshold)
        PriceQuote q = quote("cus-0001", null, "APP-3003", 1);
        assertThat(q.tax()).isEqualByComparingTo("6.32");
        assertThat(q.shipping()).isEqualByComparingTo("9.99");
        assertThat(q.total()).isEqualByComparingTo("95.31");
    }

    @Test
    void platinumStillShipsFree() {
        // cus-0004 PLATINUM/SOUTH, 1 x GRO-2001 @ 12.75
        PriceQuote q = quote("cus-0004", null, "GRO-2001", 1);
        assertThat(q.discount()).isEqualByComparingTo("1.91");
        assertThat(q.tax()).isEqualByComparingTo("0.70");
        assertThat(q.shipping()).isEqualByComparingTo("0.00");
        assertThat(q.total()).isEqualByComparingTo("11.54");
    }

    @Test
    void bulkTierAndFreeShippingCouponStack() {
        // cus-0011 GOLD/WEST, 20 x GRO-2007 @ 1.85 with FREESHIP (min spend 30)
        PriceQuote q = quote("cus-0011", "FREESHIP", "GRO-2007", 20);
        assertThat(q.subtotal()).isEqualByComparingTo("37.00");
        assertThat(q.discount()).isEqualByComparingTo("5.37");
        assertThat(q.tax()).isEqualByComparingTo("3.16");
        assertThat(q.shipping()).isEqualByComparingTo("0.00");
        assertThat(q.total()).isEqualByComparingTo("34.79");
    }

    @Test
    void seededCouponRulesAreEnforced() {
        assertThatThrownBy(() -> quote("cus-0012", "BIG20", "ELE-1002", 2))
                .isInstanceOfSatisfying(CouponRejectedException.class,
                        ex -> assertThat(ex.getReason()).isEqualTo(CouponRejectionReason.MIN_SPEND_NOT_MET));
        assertThatThrownBy(() -> quote("cus-0012", "EXPIRED15", "ELE-1002", 2))
                .isInstanceOfSatisfying(CouponRejectedException.class,
                        ex -> assertThat(ex.getReason()).isEqualTo(CouponRejectionReason.EXPIRED));
        assertThatThrownBy(() -> quote("cus-0012", "RETIRED5", "ELE-1002", 2))
                .isInstanceOfSatisfying(CouponRejectedException.class,
                        ex -> assertThat(ex.getReason()).isEqualTo(CouponRejectionReason.INACTIVE));
        assertThatThrownBy(() -> quote("cus-0012", "NOPE99", "ELE-1002", 2))
                .isInstanceOfSatisfying(CouponRejectedException.class,
                        ex -> assertThat(ex.getReason()).isEqualTo(CouponRejectionReason.UNKNOWN));
    }
}
