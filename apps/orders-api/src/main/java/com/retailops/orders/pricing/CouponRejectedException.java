package com.retailops.orders.pricing;

import com.retailops.orders.common.BusinessRuleException;

public class CouponRejectedException extends BusinessRuleException {

    private final String couponCode;
    private final CouponRejectionReason reason;

    public CouponRejectedException(String couponCode, CouponRejectionReason reason) {
        super("COUPON_REJECTED", "Coupon '" + couponCode + "' cannot be applied: " + reason);
        this.couponCode = couponCode;
        this.reason = reason;
    }

    public String getCouponCode() {
        return couponCode;
    }

    public CouponRejectionReason getReason() {
        return reason;
    }
}
