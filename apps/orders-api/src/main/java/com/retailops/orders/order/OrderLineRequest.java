package com.retailops.orders.order;

import com.retailops.orders.validation.ValidQuantity;
import com.retailops.orders.validation.ValidSku;

public record OrderLineRequest(@ValidSku String sku, @ValidQuantity int quantity) {
}
