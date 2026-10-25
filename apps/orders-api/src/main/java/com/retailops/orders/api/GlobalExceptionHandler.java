package com.retailops.orders.api;

import java.net.URI;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import com.retailops.orders.common.BusinessRuleException;
import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.inventory.InsufficientStockException;
import com.retailops.orders.order.IllegalStatusTransitionException;
import com.retailops.orders.pricing.CouponRejectedException;

/** Maps domain exceptions to RFC 7807 problem details. */
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    public static final String TYPE_BASE = "https://retailops.example/problems/";

    static ProblemDetail problem(HttpStatusCode status, String slug, String title, String detail) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(status, detail);
        pd.setType(URI.create(TYPE_BASE + slug));
        pd.setTitle(title);
        return pd;
    }

    @ExceptionHandler(NotFoundException.class)
    public ProblemDetail handleNotFound(NotFoundException ex) {
        ProblemDetail pd = problem(HttpStatus.NOT_FOUND, "not-found", "Resource not found", ex.getMessage());
        pd.setProperty("resource", ex.getResource());
        pd.setProperty("identifier", ex.getIdentifier());
        return pd;
    }

    @ExceptionHandler(DuplicateResourceException.class)
    public ProblemDetail handleDuplicate(DuplicateResourceException ex) {
        ProblemDetail pd = problem(HttpStatus.CONFLICT, "duplicate-resource", "Resource already exists",
                ex.getMessage());
        pd.setProperty("resource", ex.getResource());
        pd.setProperty("key", ex.getKey());
        return pd;
    }

    @ExceptionHandler(IllegalStatusTransitionException.class)
    public ProblemDetail handleIllegalTransition(IllegalStatusTransitionException ex) {
        ProblemDetail pd = problem(HttpStatus.CONFLICT, "illegal-status-transition",
                "Illegal order status transition", ex.getMessage());
        pd.setProperty("from", ex.getFrom().name());
        pd.setProperty("to", ex.getTo().name());
        pd.setProperty("allowed", ex.getAllowed().stream().map(Enum::name).sorted().toList());
        return pd;
    }

    @ExceptionHandler(InsufficientStockException.class)
    public ProblemDetail handleInsufficientStock(InsufficientStockException ex) {
        ProblemDetail pd = problem(HttpStatus.CONFLICT, "insufficient-stock", "Insufficient stock",
                ex.getMessage());
        pd.setProperty("sku", ex.getSku());
        pd.setProperty("requested", ex.getRequested());
        pd.setProperty("available", ex.getAvailable());
        return pd;
    }

    @ExceptionHandler(CouponRejectedException.class)
    public ProblemDetail handleCouponRejected(CouponRejectedException ex) {
        ProblemDetail pd = problem(HttpStatus.UNPROCESSABLE_ENTITY, "coupon-rejected", "Coupon rejected",
                ex.getMessage());
        pd.setProperty("code", ex.getCode());
        pd.setProperty("couponCode", ex.getCouponCode());
        pd.setProperty("reason", ex.getReason().name());
        return pd;
    }

    @ExceptionHandler(BusinessRuleException.class)
    public ProblemDetail handleBusinessRule(BusinessRuleException ex) {
        ProblemDetail pd = problem(HttpStatus.UNPROCESSABLE_ENTITY, "business-rule-violation",
                "Business rule violated", ex.getMessage());
        pd.setProperty("code", ex.getCode());
        return pd;
    }

    @ExceptionHandler(ObjectOptimisticLockingFailureException.class)
    public ProblemDetail handleOptimisticLock(ObjectOptimisticLockingFailureException ex) {
        return problem(HttpStatus.CONFLICT, "concurrent-modification", "Concurrent modification",
                "The resource was modified by another request; reload and retry");
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        List<Map<String, String>> errors = ex.getBindingResult().getFieldErrors().stream()
                .sorted(Comparator.comparing(FieldError::getField))
                .map(fe -> Map.of("field", fe.getField(),
                        "message", String.valueOf(fe.getDefaultMessage())))
                .toList();
        ProblemDetail pd = problem(status, "validation-failed", "Validation failed",
                errors.size() + " field(s) failed validation");
        pd.setProperty("errors", errors);
        return handleExceptionInternal(ex, pd, headers, status, request);
    }

    @Override
    protected ResponseEntity<Object> handleHandlerMethodValidationException(HandlerMethodValidationException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        List<Map<String, String>> errors = ex.getParameterValidationResults().stream()
                .flatMap(r -> r.getResolvableErrors().stream()
                        .map(e -> Map.of("field", String.valueOf(r.getMethodParameter().getParameterName()),
                                "message", String.valueOf(e.getDefaultMessage()))))
                .sorted(Comparator.comparing(m -> m.get("field")))
                .toList();
        ProblemDetail pd = problem(status, "validation-failed", "Validation failed",
                errors.size() + " parameter(s) failed validation");
        pd.setProperty("errors", errors);
        return handleExceptionInternal(ex, pd, headers, status, request);
    }
}
