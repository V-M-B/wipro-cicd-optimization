package com.retailops.orders.order;

import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** Body for creating an order and for requesting a price quote. */
public record CreateOrderRequest(
        @NotBlank @Size(max = 40) String customerId,
        @NotEmpty @Size(max = 100) List<@Valid OrderLineRequest> lines,
        @Pattern(regexp = "^[A-Za-z0-9]{3,32}$", message = "must be 3-32 letters or digits") String couponCode) {
}
