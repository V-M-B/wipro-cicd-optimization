package com.retailops.orders.pricing;

import java.math.BigDecimal;
import java.time.LocalDate;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "coupons")
public class CouponEntity {

    @Id
    @Column(length = 32)
    private String code;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private CouponType type;

    @Column(name = "amount", nullable = false, precision = 10, scale = 2)
    private BigDecimal value;

    @Column(name = "min_spend", precision = 12, scale = 2)
    private BigDecimal minSpend;

    @Column(name = "max_discount", precision = 12, scale = 2)
    private BigDecimal maxDiscount;

    @Column(name = "valid_from")
    private LocalDate validFrom;

    @Column(name = "expires_on")
    private LocalDate expiresOn;

    @Column(nullable = false)
    private boolean active;

    protected CouponEntity() {
    }

    public CouponEntity(Coupon coupon) {
        this.code = coupon.code();
        this.type = coupon.type();
        this.value = coupon.value();
        this.minSpend = coupon.minSpend();
        this.maxDiscount = coupon.maxDiscount();
        this.validFrom = coupon.validFrom();
        this.expiresOn = coupon.expiresOn();
        this.active = coupon.active();
    }

    public Coupon toCoupon() {
        return new Coupon(code, type, value, minSpend, maxDiscount, validFrom, expiresOn, active);
    }

    public String getCode() {
        return code;
    }

    public boolean isActive() {
        return active;
    }
}
