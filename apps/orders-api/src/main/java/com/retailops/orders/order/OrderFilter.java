package com.retailops.orders.order;

import java.time.OffsetDateTime;

import org.springframework.data.jpa.domain.Specification;

import com.retailops.orders.common.BusinessRuleException;
import com.retailops.schemas.OrderStatus;

/**
 * Optional list filters; null fields are ignored. {@code from} is inclusive, {@code to} exclusive.
 * The customer id is trimmed, so {@code ?customerId=%20cus-1} matches {@code cus-1}.
 */
public record OrderFilter(String customerId, OrderStatus status, OffsetDateTime from, OffsetDateTime to) {

    public OrderFilter {
        if (customerId != null) {
            customerId = customerId.strip();
            if (customerId.isEmpty()) {
                customerId = null;
            }
        }
        if (from != null && to != null && !from.isBefore(to)) {
            throw new BusinessRuleException("INVALID_DATE_RANGE", "'from' must be before 'to'");
        }
    }

    public static OrderFilter none() {
        return new OrderFilter(null, null, null, null);
    }

    public boolean isEmpty() {
        return customerId == null && status == null && from == null && to == null;
    }

    public Specification<OrderEntity> toSpecification() {
        Specification<OrderEntity> spec = (root, query, cb) -> cb.conjunction();
        if (customerId != null) {
            String c = customerId;
            spec = spec.and((root, query, cb) -> cb.equal(root.get("customerId"), c));
        }
        if (status != null) {
            OrderStatus s = status;
            spec = spec.and((root, query, cb) -> cb.equal(root.get("status"), s));
        }
        if (from != null) {
            OffsetDateTime f = from;
            spec = spec.and((root, query, cb) -> cb.greaterThanOrEqualTo(root.get("createdAt"), f));
        }
        if (to != null) {
            OffsetDateTime t = to;
            spec = spec.and((root, query, cb) -> cb.lessThan(root.get("createdAt"), t));
        }
        return spec;
    }
}
