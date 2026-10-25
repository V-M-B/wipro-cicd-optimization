package com.retailops.orders.order;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderBy;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

import org.hibernate.annotations.BatchSize;

import com.retailops.orders.pricing.PriceBreakdown;
import com.retailops.schemas.OrderStatus;

@Entity
@Table(name = "orders")
public class OrderEntity {

    @Id
    @Column(length = 40)
    private String id;

    @Column(name = "customer_id", nullable = false, length = 40)
    private String customerId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OrderStatus status;

    @Column(name = "coupon_code", length = 32)
    private String couponCode;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal subtotal;

    @Column(name = "discount_total", nullable = false, precision = 12, scale = 2)
    private BigDecimal discountTotal;

    @Column(name = "tax_total", nullable = false, precision = 12, scale = 2)
    private BigDecimal taxTotal;

    @Column(name = "shipping_total", nullable = false, precision = 12, scale = 2)
    private BigDecimal shippingTotal;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal total;

    @Column(name = "created_at", nullable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    @Version
    @Column(nullable = false)
    private long version;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("lineNo ASC")
    @BatchSize(size = 50)
    private List<OrderLineEntity> lines = new ArrayList<>();

    protected OrderEntity() {
    }

    public OrderEntity(String id, String customerId, String couponCode, PriceBreakdown price, OffsetDateTime now) {
        this.id = id;
        this.customerId = customerId;
        this.couponCode = couponCode;
        this.status = OrderStatus.CREATED;
        this.subtotal = price.subtotal();
        this.discountTotal = price.discount();
        this.taxTotal = price.tax();
        this.shippingTotal = price.shipping();
        this.total = price.total();
        this.createdAt = now;
        this.updatedAt = now;
    }

    public void addLine(OrderLineEntity line) {
        line.attachTo(this);
        lines.add(line);
    }

    /** Applies a status change through the state machine; returns the previous status. */
    public OrderStatus transitionTo(OrderStatus target, OffsetDateTime now) {
        OrderStatus previous = status;
        status = OrderStateMachine.transition(status, target);
        updatedAt = now;
        return previous;
    }

    public int totalUnits() {
        return lines.stream().mapToInt(OrderLineEntity::getQuantity).sum();
    }

    public String getId() {
        return id;
    }

    public String getCustomerId() {
        return customerId;
    }

    public OrderStatus getStatus() {
        return status;
    }

    public String getCouponCode() {
        return couponCode;
    }

    public BigDecimal getSubtotal() {
        return subtotal;
    }

    public BigDecimal getDiscountTotal() {
        return discountTotal;
    }

    public BigDecimal getTaxTotal() {
        return taxTotal;
    }

    public BigDecimal getShippingTotal() {
        return shippingTotal;
    }

    public BigDecimal getTotal() {
        return total;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public long getVersion() {
        return version;
    }

    public List<OrderLineEntity> getLines() {
        return Collections.unmodifiableList(lines);
    }
}
