package com.retailops.orders.pricing;

public enum CouponRejectionReason {
    UNKNOWN,
    INACTIVE,
    NOT_YET_VALID,
    EXPIRED,
    MIN_SPEND_NOT_MET
}
