package com.retailops.orders.catalog;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import com.fasterxml.jackson.databind.JsonNode;
import com.retailops.orders.support.HttpIntegrationSupport;

/** Catalog, inventory and actuator endpoints over HTTP (shares the cached context of the lifecycle IT). */
class ProductCatalogHttpIT extends HttpIntegrationSupport {

    @Test
    void createdProductIsRetrievableWithInitialStock() {
        String sku = nextSku("CAT");
        ResponseEntity<JsonNode> created = rest.postForEntity("/api/products", Map.of("sku", sku, "name", "Teapot",
                "category", "HOME", "unitPrice", "19.5", "initialStock", 12), JsonNode.class);
        assertThat(created.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(created.getHeaders().getLocation()).hasToString("/api/products/" + sku);

        JsonNode fetched = rest.getForObject("/api/products/" + sku.toLowerCase(), JsonNode.class);
        assertThat(fetched.get("name").asText()).isEqualTo("Teapot");
        assertThat(fetched.get("unitPrice").decimalValue()).isEqualByComparingTo("19.50");
        assertThat(stock(sku).get("onHand").asInt()).isEqualTo(12);
    }

    @Test
    void duplicateAndInvalidProductsAreRejected() {
        String sku = createProduct("CAT", "5.00", 1);
        ResponseEntity<JsonNode> duplicate = rest.postForEntity("/api/products", Map.of("sku", sku, "name", "Again",
                "category", "HOME", "unitPrice", "5.00", "initialStock", 1), JsonNode.class);
        assertThat(duplicate.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);

        ResponseEntity<JsonNode> invalid = rest.postForEntity("/api/products", Map.of("sku", "bad", "name", "",
                "category", "HOME", "unitPrice", "-1", "initialStock", 1), JsonNode.class);
        assertThat(invalid.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        List<String> fields = new ArrayList<>();
        invalid.getBody().get("errors").forEach(e -> fields.add(e.get("field").asText()));
        assertThat(fields).containsExactly("name", "sku", "unitPrice");
    }

    @Test
    void restockIncreasesOnHand() {
        String sku = createProduct("CAT", "5.00", 3);
        ResponseEntity<JsonNode> response = rest.postForEntity("/api/inventory/" + sku + "/restock",
                Map.of("quantity", 47), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().get("onHand").asInt()).isEqualTo(50);
    }

    @Test
    void activeOnlyListingHidesDiscontinuedSeedProduct() {
        JsonNode toys = rest.getForObject("/api/products?category=TOYS&activeOnly=true", JsonNode.class);
        List<String> skus = new ArrayList<>();
        toys.forEach(p -> skus.add(p.get("sku").asText()));
        assertThat(skus).contains("TOY-5001", "TOY-5007").doesNotContain("TOY-5008").isSorted();

        JsonNode all = rest.getForObject("/api/products?category=TOYS", JsonNode.class);
        assertThat(all).hasSize(skus.size() + 1);
    }

    @Test
    void actuatorHealthIsUp() {
        JsonNode health = rest.getForObject("/actuator/health", JsonNode.class);
        assertThat(health.get("status").asText()).isEqualTo("UP");
    }
}
