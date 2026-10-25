package com.retailops.orders.order;

import jakarta.validation.constraints.NotNull;

import com.retailops.schemas.OrderStatus;

public record StatusTransitionRequest(@NotNull OrderStatus target) {
}
