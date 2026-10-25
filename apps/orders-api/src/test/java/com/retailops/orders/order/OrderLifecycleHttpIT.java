package com.retailops.orders.order;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import com.fasterxml.jackson.databind.JsonNode;
import com.retailops.orders.api.GlobalExceptionHandler;
import com.retailops.orders.support.HttpIntegrationSupport;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.Region;

/** End-to-end order lifecycle over HTTP against a real PostgreSQL. */
class OrderLifecycleHttpIT extends HttpIntegrationSupport {

    private String createdOrder(String customer, String sku, int qty) {
        ResponseEntity<JsonNode> created = placeOrder(customer, null, sku, qty);
        assertThat(created.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        return created.getBody().get("id").asText();
    }

    @Test
    void fullLifecycleReservesThenConsumesStock() {
        String sku = createProduct("LIF", "10.00", 50);
        String customer = createCustomer(CustomerTier.STANDARD, Region.NORTH);

        ResponseEntity<JsonNode> created = placeOrder(customer, null, sku, 4);
        assertThat(created.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(created.getHeaders().getLocation()).hasToString("/api/orders/" + created.getBody().get("id").asText());
        assertThat(created.getBody().get("status").asText()).isEqualTo("CREATED");
        // 40.00 + 8% tax 3.20 + NORTH shipping 5.99
        assertThat(created.getBody().get("total").decimalValue()).isEqualByComparingTo("49.19");
        String id = created.getBody().get("id").asText();
        assertThat(stock(sku).get("reserved").asInt()).isEqualTo(4);
        assertThat(stock(sku).get("available").asInt()).isEqualTo(46);

        assertThat(transition(id, OrderStatus.PAID).getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(stock(sku).get("reserved").asInt()).isEqualTo(4);

        assertThat(transition(id, OrderStatus.SHIPPED).getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(stock(sku).get("onHand").asInt()).isEqualTo(46);
        assertThat(stock(sku).get("reserved").asInt()).isZero();

        assertThat(transition(id, OrderStatus.DELIVERED).getBody().get("status").asText()).isEqualTo("DELIVERED");
        JsonNode fetched = rest.getForObject("/api/orders/" + id, JsonNode.class);
        assertThat(fetched.get("status").asText()).isEqualTo("DELIVERED");
        assertThat(fetched.get("lines").get(0).get("quantity").asInt()).isEqualTo(4);
    }

    @Test
    void cancellingCreatedOrderReleasesStock() {
        String sku = createProduct("LIF", "5.00", 20);
        String id = createdOrder(createCustomer(CustomerTier.SILVER, Region.SOUTH), sku, 7);
        assertThat(stock(sku).get("available").asInt()).isEqualTo(13);

        assertThat(transition(id, OrderStatus.CANCELLED).getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(stock(sku).get("available").asInt()).isEqualTo(20);
        assertThat(stock(sku).get("onHand").asInt()).isEqualTo(20);
    }

    @Test
    void cancellingPaidOrderReleasesStock() {
        String sku = createProduct("LIF", "5.00", 20);
        String id = createdOrder(createCustomer(CustomerTier.GOLD, Region.EAST), sku, 3);
        transition(id, OrderStatus.PAID);
        assertThat(transition(id, OrderStatus.CANCELLED).getBody().get("status").asText()).isEqualTo("CANCELLED");
        assertThat(stock(sku).get("reserved").asInt()).isZero();
    }

    @Test
    void deliveredOrderCannotBeCancelled() {
        String sku = createProduct("LIF", "5.00", 20);
        String id = createdOrder(createCustomer(CustomerTier.STANDARD, Region.WEST), sku, 1);
        transition(id, OrderStatus.PAID);
        transition(id, OrderStatus.SHIPPED);
        transition(id, OrderStatus.DELIVERED);

        ResponseEntity<JsonNode> rejected = transition(id, OrderStatus.CANCELLED);
        assertThat(rejected.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
        assertThat(rejected.getBody().get("type").asText())
                .isEqualTo(GlobalExceptionHandler.TYPE_BASE + "illegal-status-transition");
        assertThat(rejected.getBody().get("allowed")).isEmpty();
        assertThat(stock(sku).get("onHand").asInt()).isEqualTo(19);
    }

    @Test
    void failedOrderLeavesNoPartialReservation() {
        String plenty = createProduct("LIF", "3.00", 10);
        String scarce = createProduct("LIF", "3.00", 1);
        String customer = createCustomer(CustomerTier.STANDARD, Region.NORTH);

        ResponseEntity<JsonNode> response = placeOrder(customer, null, plenty, 5, scarce, 2);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
        assertThat(response.getBody().get("sku").asText()).isEqualTo(scarce);
        assertThat(response.getBody().get("available").asInt()).isEqualTo(1);
        assertThat(stock(plenty).get("reserved").asInt()).isZero();
        assertThat(stock(scarce).get("reserved").asInt()).isZero();
    }

    @Test
    void orderTotalMatchesQuoteWithCoupon() {
        String sku = createProduct("LIF", "30.00", 30);
        String customer = createCustomer(CustomerTier.GOLD, Region.WEST);

        JsonNode quote = rest.postForObject("/api/orders/quote", orderBody(customer, "welcome10", sku, 3), JsonNode.class);
        ResponseEntity<JsonNode> order = placeOrder(customer, "welcome10", sku, 3);

        // 90.00 - 9.00 tier = 81.00; WELCOME10 -8.10 -> 72.90; tax 9% 6.56; shipping 6.99 (72.90 < 75)
        assertThat(quote.get("discount").decimalValue()).isEqualByComparingTo("17.10");
        assertThat(quote.get("total").decimalValue()).isEqualByComparingTo("86.45");
        assertThat(order.getBody().get("total").decimalValue()).isEqualByComparingTo(quote.get("total").decimalValue());
        assertThat(order.getBody().get("couponCode").asText()).isEqualTo("WELCOME10");
    }

    @Test
    void expiredCouponIsRejected() {
        String sku = createProduct("LIF", "30.00", 30);
        ResponseEntity<JsonNode> response = placeOrder(createCustomer(CustomerTier.STANDARD, Region.EAST), "EXPIRED15",
                sku, 1);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNPROCESSABLE_ENTITY);
        assertThat(response.getBody().get("reason").asText()).isEqualTo("EXPIRED");
        assertThat(stock(sku).get("reserved").asInt()).isZero();
    }

    @Test
    void deactivatedProductCannotBeOrdered() {
        String sku = createProduct("LIF", "8.00", 30);
        rest.postForEntity("/api/products/" + sku + "/deactivate", null, JsonNode.class);
        ResponseEntity<JsonNode> response = placeOrder(createCustomer(CustomerTier.STANDARD, Region.EAST), null, sku, 1);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNPROCESSABLE_ENTITY);
        assertThat(response.getBody().get("code").asText()).isEqualTo("PRODUCT_INACTIVE");
    }

    @Test
    void duplicateLinesAreMergedAndPriceChangesDoNotRewriteHistory() {
        String sku = createProduct("LIF", "12.00", 30);
        String customer = createCustomer(CustomerTier.STANDARD, Region.SOUTH);
        ResponseEntity<JsonNode> order = placeOrder(customer, null, sku, 2, sku, 3);
        assertThat(order.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(order.getBody().get("lines")).hasSize(1);
        assertThat(order.getBody().get("lines").get(0).get("quantity").asInt()).isEqualTo(5);

        rest.put("/api/products/" + sku + "/price", Map.of("unitPrice", new BigDecimal("99.00")));
        JsonNode fetched = rest.getForObject("/api/orders/" + order.getBody().get("id").asText(), JsonNode.class);
        assertThat(fetched.get("lines").get(0).get("unitPrice").decimalValue()).isEqualByComparingTo("12.00");
    }
}
