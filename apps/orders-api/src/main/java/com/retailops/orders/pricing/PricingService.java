package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.LocalDate;

import org.springframework.stereotype.Service;

import com.retailops.orders.common.BusinessRuleException;

/**
 * Prices an order. Order of operations (each amount rounded HALF_EVEN to 2dp):
 * <ol>
 * <li>line subtotal = unit price x quantity; subtotal = sum of line subtotals</li>
 * <li>bulk discount per line by quantity tier</li>
 * <li>tier discount on (subtotal - bulk)</li>
 * <li>coupon on (subtotal - bulk - tier); min-spend is checked against the subtotal</li>
 * <li>tax on the net merchandise amount by region</li>
 * <li>shipping by region/units unless free (threshold, PLATINUM, coupon)</li>
 * <li>total = net + tax + shipping</li>
 * </ol>
 */
@Service
public class PricingService {

    private final TierDiscountPolicy tierDiscountPolicy;
    private final BulkDiscountPolicy bulkDiscountPolicy;
    private final TaxPolicy taxPolicy;
    private final ShippingPolicy shippingPolicy;
    private final CouponEvaluator couponEvaluator;
    private final Clock clock;

    public PricingService(TierDiscountPolicy tierDiscountPolicy, BulkDiscountPolicy bulkDiscountPolicy,
            TaxPolicy taxPolicy, ShippingPolicy shippingPolicy, CouponEvaluator couponEvaluator, Clock clock) {
        this.tierDiscountPolicy = tierDiscountPolicy;
        this.bulkDiscountPolicy = bulkDiscountPolicy;
        this.taxPolicy = taxPolicy;
        this.shippingPolicy = shippingPolicy;
        this.couponEvaluator = couponEvaluator;
        this.clock = clock;
    }

    /** Convenience factory wiring the default policies, used by tests and tools. */
    public static PricingService withDefaults(PricingProperties properties, Clock clock) {
        return new PricingService(new TierDiscountPolicy(), new BulkDiscountPolicy(), new TaxPolicy(properties),
                new ShippingPolicy(properties), new CouponEvaluator(), clock);
    }

    public PriceBreakdown quote(PricingRequest request) {
        if (request.lines().isEmpty()) {
            throw new BusinessRuleException("EMPTY_ORDER", "An order needs at least one line");
        }
        BigDecimal subtotal = Money.ZERO;
        BigDecimal bulkDiscount = Money.ZERO;
        int units = 0;
        for (PricedLine line : request.lines()) {
            BigDecimal lineSubtotal = line.lineSubtotal();
            subtotal = subtotal.add(lineSubtotal);
            bulkDiscount = bulkDiscount.add(bulkDiscountPolicy.discount(lineSubtotal, line.quantity()));
            units = Math.addExact(units, line.quantity());
        }
        BigDecimal afterBulk = subtotal.subtract(bulkDiscount);
        BigDecimal tierDiscount = tierDiscountPolicy.discount(afterBulk, request.tier());
        BigDecimal afterTier = afterBulk.subtract(tierDiscount);

        LocalDate date = request.pricingDate() != null ? request.pricingDate() : LocalDate.now(clock);
        CouponOutcome coupon = request.coupon() == null
                ? CouponOutcome.NONE
                : couponEvaluator.evaluate(request.coupon(), subtotal, afterTier, date);

        BigDecimal net = afterTier.subtract(coupon.discount());
        BigDecimal tax = taxPolicy.tax(net, request.region());
        BigDecimal shipping = shippingPolicy.cost(net, units, request.region(), request.tier(), coupon.freeShipping());
        BigDecimal total = Money.sum(net, tax, shipping);
        return new PriceBreakdown(subtotal, bulkDiscount, tierDiscount, coupon.discount(), tax, shipping, total);
    }
}
