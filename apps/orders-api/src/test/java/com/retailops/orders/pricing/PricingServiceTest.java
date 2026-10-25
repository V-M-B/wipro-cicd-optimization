package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import com.retailops.orders.common.BusinessRuleException;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.PriceQuote;
import com.retailops.schemas.Region;

class PricingServiceTest {

    private final PricingService service = TestFixtures.defaultPricingService();

    private static PricedLine line(String sku, int qty, String price) {
        return new PricedLine(sku, qty, new BigDecimal(price));
    }

    @Test
    void simpleStandardOrderPaysTaxAndShipping() {
        PriceBreakdown b = service.quote(new PricingRequest(List.of(line("ELE-1001", 2, "24.99")),
                CustomerTier.STANDARD, Region.NORTH));
        assertThat(b.subtotal()).isEqualTo(new BigDecimal("49.98"));
        assertThat(b.discount()).isEqualTo(new BigDecimal("0.00"));
        assertThat(b.tax()).isEqualTo(new BigDecimal("4.00"));
        assertThat(b.shipping()).isEqualTo(new BigDecimal("5.99"));
        assertThat(b.total()).isEqualTo(new BigDecimal("59.97"));
    }

    @Test
    void bulkThenTierDiscountsAreStacked() {
        PriceBreakdown b = service.quote(new PricingRequest(List.of(line("GRO-2003", 10, "8.45")),
                CustomerTier.GOLD, Region.WEST));
        assertThat(b.subtotal()).isEqualTo(new BigDecimal("84.50"));
        assertThat(b.bulkDiscount()).isEqualTo(new BigDecimal("1.69"));
        assertThat(b.tierDiscount()).isEqualTo(new BigDecimal("8.28"));
        assertThat(b.netMerchandise()).isEqualTo(new BigDecimal("74.53"));
        assertThat(b.tax()).isEqualTo(new BigDecimal("6.71"));
        // net below 75.00 -> 6.99 base + 5 extra units x 0.50
        assertThat(b.shipping()).isEqualTo(new BigDecimal("9.49"));
        assertThat(b.total()).isEqualTo(new BigDecimal("90.73"));
    }

    @Test
    void platinumGetsTierDiscountAndFreeShipping() {
        PriceBreakdown b = service.quote(new PricingRequest(List.of(line("ELE-1006", 1, "7.49")),
                CustomerTier.PLATINUM, Region.SOUTH));
        assertThat(b.tierDiscount()).isEqualTo(new BigDecimal("1.12"));
        assertThat(b.tax()).isEqualTo(new BigDecimal("0.41"));
        assertThat(b.shipping()).isEqualTo(Money.ZERO);
        assertThat(b.total()).isEqualTo(new BigDecimal("6.78"));
    }

    @Test
    void freeShippingCouponWithTierDiscount() {
        Coupon coupon = Coupon.freeShipping("FREESHIP").withMinSpend("30.00");
        PriceBreakdown b = service.quote(new PricingRequest(List.of(line("HOM-4006", 3, "12.10")),
                CustomerTier.SILVER, Region.EAST, coupon, null));
        assertThat(b.tierDiscount()).isEqualTo(new BigDecimal("1.82"));
        assertThat(b.couponDiscount()).isEqualTo(Money.ZERO);
        assertThat(b.tax()).isEqualTo(new BigDecimal("2.50"));
        assertThat(b.shipping()).isEqualTo(Money.ZERO);
        assertThat(b.total()).isEqualTo(new BigDecimal("36.98"));
    }

    @Test
    void fixedCouponLargerThanOrderLeavesOnlyShipping() {
        PriceBreakdown b = service.quote(new PricingRequest(List.of(line("GRO-2005", 1, "3.15")),
                CustomerTier.STANDARD, Region.NORTH, Coupon.fixed("BIG", "15"), null));
        assertThat(b.couponDiscount()).isEqualTo(new BigDecimal("3.15"));
        assertThat(b.tax()).isEqualTo(new BigDecimal("0.00"));
        assertThat(b.total()).isEqualTo(new BigDecimal("5.99"));
    }

    @Test
    void bulkDiscountIsPerLineNotPerOrder() {
        PriceBreakdown split = service.quote(new PricingRequest(
                List.of(line("AAA-0001", 9, "10.00"), line("AAA-0002", 9, "10.00")), CustomerTier.STANDARD,
                Region.NORTH));
        PriceBreakdown single = service.quote(new PricingRequest(List.of(line("AAA-0001", 18, "10.00")),
                CustomerTier.STANDARD, Region.NORTH));
        assertThat(split.bulkDiscount()).isEqualTo(Money.ZERO);
        assertThat(single.bulkDiscount()).isEqualTo(new BigDecimal("3.60"));
    }

    @Test
    void lineOrderDoesNotChangeThePrice() {
        List<PricedLine> lines = new ArrayList<>(List.of(line("ELE-1002", 3, "89.50"), line("GRO-2001", 12, "12.75"),
                line("TOY-5002", 25, "18.50")));
        PriceBreakdown forward = service.quote(new PricingRequest(lines, CustomerTier.GOLD, Region.EAST));
        Collections.reverse(lines);
        PriceBreakdown reversed = service.quote(new PricingRequest(lines, CustomerTier.GOLD, Region.EAST));
        assertThat(reversed).isEqualTo(forward);
    }

    @Test
    void pricingDateDefaultsToClockDate() {
        Coupon todayOnly = Coupon.fixed("TODAY", "2").withValidity(TestFixtures.PRICING_DATE, TestFixtures.PRICING_DATE);
        PricingRequest request = new PricingRequest(List.of(line("ELE-1001", 1, "24.99")), CustomerTier.STANDARD,
                Region.NORTH, todayOnly, null);
        assertThat(service.quote(request).couponDiscount()).isEqualTo(new BigDecimal("2.00"));
    }

    @Test
    void explicitPricingDateOverridesClock() {
        Coupon todayOnly = Coupon.fixed("TODAY", "2").withValidity(TestFixtures.PRICING_DATE, TestFixtures.PRICING_DATE);
        PricingRequest request = new PricingRequest(List.of(line("ELE-1001", 1, "24.99")), CustomerTier.STANDARD,
                Region.NORTH, todayOnly, TestFixtures.PRICING_DATE.plusDays(1));
        assertThatThrownBy(() -> service.quote(request))
                .isInstanceOfSatisfying(CouponRejectedException.class,
                        ex -> assertThat(ex.getReason()).isEqualTo(CouponRejectionReason.EXPIRED));
    }

    @Test
    void emptyOrderIsRejected() {
        assertThatThrownBy(() -> service.quote(new PricingRequest(List.of(), CustomerTier.STANDARD, Region.NORTH)))
                .isInstanceOfSatisfying(BusinessRuleException.class,
                        ex -> assertThat(ex.getCode()).isEqualTo("EMPTY_ORDER"));
    }

    @Test
    void priceQuoteCollapsesDiscounts() {
        PriceQuote quote = service.quote(new PricingRequest(List.of(line("GRO-2003", 10, "8.45")),
                CustomerTier.GOLD, Region.WEST)).toPriceQuote();
        assertThat(quote.discount()).isEqualTo(new BigDecimal("9.97"));
        assertThat(quote.total()).isEqualTo(new BigDecimal("90.73"));
    }

    @ParameterizedTest(name = "seed {0}")
    @ValueSource(longs = {7, 42, 31337})
    void totalAlwaysEqualsNetPlusTaxPlusShipping(long seed) {
        Random random = new Random(seed);
        List<PricedLine> lines = new ArrayList<>();
        int count = 1 + random.nextInt(5);
        for (int i = 0; i < count; i++) {
            BigDecimal price = BigDecimal.valueOf(1 + random.nextInt(30000), 2);
            lines.add(new PricedLine("RND-%04d".formatted(i), 1 + random.nextInt(150), price));
        }
        CustomerTier tier = CustomerTier.values()[random.nextInt(4)];
        Region region = Region.values()[random.nextInt(4)];
        PriceBreakdown b = service.quote(new PricingRequest(lines, tier, region, Coupon.percentage("P", "7"), null));
        assertThat(b.total()).isEqualTo(b.subtotal().subtract(b.discount()).add(b.tax()).add(b.shipping()));
        assertThat(b.netMerchandise().signum()).isGreaterThanOrEqualTo(0);
        assertThat(b.total().scale()).isEqualTo(2);
    }
}
