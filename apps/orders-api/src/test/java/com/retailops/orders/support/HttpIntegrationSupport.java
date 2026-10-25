package com.retailops.orders.support;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import com.fasterxml.jackson.databind.JsonNode;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.OrderStatus;
import com.retailops.schemas.Region;

/** Base for HTTP-level integration tests: real server on a random port + Testcontainers PostgreSQL. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(PostgresTestcontainersConfig.class)
public abstract class HttpIntegrationSupport {

    private static final AtomicInteger SEQUENCE = new AtomicInteger(1000);

    @Autowired
    protected TestRestTemplate rest;

    protected static String nextSku(String prefix) {
        return "%s-%04d".formatted(prefix, SEQUENCE.incrementAndGet());
    }

    protected String createProduct(String prefix, String price, int stock) {
        String sku = nextSku(prefix);
        ResponseEntity<JsonNode> response = rest.postForEntity("/api/products", Map.of("sku", sku,
                "name", "IT product " + sku, "category", "HOME", "unitPrice", price, "initialStock", stock),
                JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        return sku;
    }

    protected String createCustomer(CustomerTier tier, Region region) {
        String email = "it" + SEQUENCE.incrementAndGet() + "@it.example.com";
        ResponseEntity<JsonNode> response = rest.postForEntity("/api/customers",
                Map.of("name", "IT Customer", "email", email, "tier", tier, "region", region), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        return response.getBody().get("id").asText();
    }

    protected JsonNode stock(String sku) {
        ResponseEntity<JsonNode> response = rest.getForEntity("/api/inventory/" + sku, JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        return response.getBody();
    }

    protected static Map<String, Object> orderBody(String customerId, String coupon, Object... skuQty) {
        List<Map<String, Object>> lines = new ArrayList<>();
        for (int i = 0; i < skuQty.length; i += 2) {
            lines.add(Map.of("sku", skuQty[i], "quantity", skuQty[i + 1]));
        }
        Map<String, Object> body = new HashMap<>();
        body.put("customerId", customerId);
        body.put("lines", lines);
        if (coupon != null) {
            body.put("couponCode", coupon);
        }
        return body;
    }

    protected ResponseEntity<JsonNode> placeOrder(String customerId, String coupon, Object... skuQty) {
        return rest.postForEntity("/api/orders", orderBody(customerId, coupon, skuQty), JsonNode.class);
    }

    protected ResponseEntity<JsonNode> transition(String orderId, OrderStatus target) {
        return rest.postForEntity("/api/orders/" + orderId + "/transitions", Map.of("target", target), JsonNode.class);
    }
}
