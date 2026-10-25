package com.retailops.orders.api;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.util.EnumSet;

import org.junit.jupiter.api.Test;
import org.springframework.http.ProblemDetail;
import org.springframework.orm.ObjectOptimisticLockingFailureException;

import com.retailops.orders.common.BusinessRuleException;
import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.inventory.InsufficientStockException;
import com.retailops.orders.order.IllegalStatusTransitionException;
import com.retailops.orders.pricing.CouponRejectedException;
import com.retailops.orders.pricing.CouponRejectionReason;
import com.retailops.schemas.OrderStatus;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    private static URI type(String slug) {
        return URI.create(GlobalExceptionHandler.TYPE_BASE + slug);
    }

    @Test
    void notFound() {
        ProblemDetail pd = handler.handleNotFound(new NotFoundException("Order", "ord-1"));
        assertThat(pd.getStatus()).isEqualTo(404);
        assertThat(pd.getType()).isEqualTo(type("not-found"));
        assertThat(pd.getTitle()).isEqualTo("Resource not found");
        assertThat(pd.getDetail()).isEqualTo("Order 'ord-1' was not found");
        assertThat(pd.getProperties()).containsEntry("resource", "Order").containsEntry("identifier", "ord-1");
    }

    @Test
    void duplicate() {
        ProblemDetail pd = handler.handleDuplicate(new DuplicateResourceException("Customer", "a@b.co"));
        assertThat(pd.getStatus()).isEqualTo(409);
        assertThat(pd.getProperties()).containsEntry("key", "a@b.co");
    }

    @Test
    void illegalTransitionListsAllowedTargetsSorted() {
        ProblemDetail pd = handler.handleIllegalTransition(new IllegalStatusTransitionException(OrderStatus.CREATED,
                OrderStatus.DELIVERED, EnumSet.of(OrderStatus.PAID, OrderStatus.CANCELLED)));
        assertThat(pd.getStatus()).isEqualTo(409);
        assertThat(pd.getType()).isEqualTo(type("illegal-status-transition"));
        assertThat(pd.getProperties()).containsEntry("allowed", java.util.List.of("CANCELLED", "PAID"));
    }

    @Test
    void insufficientStock() {
        ProblemDetail pd = handler.handleInsufficientStock(new InsufficientStockException("ELE-1001", 5, 2));
        assertThat(pd.getStatus()).isEqualTo(409);
        assertThat(pd.getProperties()).containsEntry("requested", 5).containsEntry("available", 2);
    }

    @Test
    void couponRejected() {
        ProblemDetail pd = handler.handleCouponRejected(
                new CouponRejectedException("BIG20", CouponRejectionReason.MIN_SPEND_NOT_MET));
        assertThat(pd.getStatus()).isEqualTo(422);
        assertThat(pd.getProperties()).containsEntry("reason", "MIN_SPEND_NOT_MET").containsEntry("couponCode", "BIG20");
    }

    @Test
    void businessRule() {
        ProblemDetail pd = handler.handleBusinessRule(new BusinessRuleException("EMPTY_ORDER", "empty"));
        assertThat(pd.getStatus()).isEqualTo(422);
        assertThat(pd.getType()).isEqualTo(type("business-rule-violation"));
        assertThat(pd.getProperties()).containsEntry("code", "EMPTY_ORDER");
    }

    @Test
    void optimisticLock() {
        ProblemDetail pd = handler.handleOptimisticLock(new ObjectOptimisticLockingFailureException(Object.class, "x"));
        assertThat(pd.getStatus()).isEqualTo(409);
        assertThat(pd.getType()).isEqualTo(type("concurrent-modification"));
    }
}
