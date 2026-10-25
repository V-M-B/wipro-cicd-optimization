package com.retailops.orders.validation;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import com.retailops.orders.catalog.CreateProductRequest;
import com.retailops.orders.catalog.PriceUpdateRequest;
import com.retailops.orders.customer.CreateCustomerRequest;
import com.retailops.orders.inventory.RestockRequest;
import com.retailops.orders.order.CreateOrderRequest;
import com.retailops.orders.order.OrderLineRequest;
import com.retailops.orders.order.StatusTransitionRequest;
import com.retailops.schemas.Category;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

/** Bean Validation constraints on the request DTOs, using the real Hibernate Validator. */
class RequestValidationTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void init() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void close() {
        factory.close();
    }

    private static Set<String> invalidPaths(Object bean) {
        return validator.validate(bean).stream().map(ConstraintViolation::getPropertyPath).map(Object::toString)
                .collect(Collectors.toSet());
    }

    private static CreateProductRequest product(String sku, String price) {
        return new CreateProductRequest(sku, "Desk Lamp", Category.HOME, price == null ? null : new BigDecimal(price), 5);
    }

    @Test
    void validProductPasses() {
        assertThat(invalidPaths(product("HOM-4999", "27.75"))).isEmpty();
    }

    @Test
    void productWithBadSkuFails() {
        assertThat(invalidPaths(product("lamp", "27.75"))).containsExactly("sku");
    }

    @Test
    void productPriceMustBePositiveWithTwoDecimals() {
        assertThat(invalidPaths(product("HOM-4999", "0.00"))).containsExactly("unitPrice");
        assertThat(invalidPaths(product("HOM-4999", "1.999"))).containsExactly("unitPrice");
        assertThat(invalidPaths(product("HOM-4999", null))).containsExactly("unitPrice");
    }

    @Test
    void productNeedsNameCategoryAndNonNegativeStock() {
        assertThat(invalidPaths(new CreateProductRequest("HOM-4999", " ", null, BigDecimal.TEN, -1)))
                .containsExactlyInAnyOrder("name", "category", "initialStock");
    }

    @Test
    void customerEmailIsValidated() {
        assertThat(invalidPaths(new CreateCustomerRequest("Asha", "not-an-email", CustomerTier.GOLD, Region.EAST)))
                .containsExactly("email");
        assertThat(invalidPaths(new CreateCustomerRequest("Asha", "asha@example.com", CustomerTier.GOLD, Region.EAST)))
                .isEmpty();
    }

    @Test
    void customerNeedsTierAndRegion() {
        assertThat(invalidPaths(new CreateCustomerRequest("Asha", "asha@example.com", null, null)))
                .containsExactlyInAnyOrder("tier", "region");
    }

    @Test
    void orderLinesAreValidatedIndividually() {
        CreateOrderRequest request = new CreateOrderRequest("cus-1",
                List.of(new OrderLineRequest("ELE-1001", 1), new OrderLineRequest("bad", 0)), null);
        assertThat(invalidPaths(request)).containsExactlyInAnyOrder("lines[1].sku", "lines[1].quantity");
    }

    @Test
    void orderNeedsCustomerAndLines() {
        assertThat(invalidPaths(new CreateOrderRequest("", List.of(), null)))
                .containsExactlyInAnyOrder("customerId", "lines");
    }

    @Test
    void couponCodeFormatIsValidated() {
        List<OrderLineRequest> lines = List.of(new OrderLineRequest("ELE-1001", 1));
        assertThat(invalidPaths(new CreateOrderRequest("cus-1", lines, "SAVE 5!"))).containsExactly("couponCode");
        assertThat(invalidPaths(new CreateOrderRequest("cus-1", lines, "SAVE5"))).isEmpty();
    }

    @Test
    void transitionNeedsTarget() {
        assertThat(invalidPaths(new StatusTransitionRequest(null))).containsExactly("target");
    }

    @Test
    void restockAndPriceUpdateBounds() {
        assertThat(invalidPaths(new RestockRequest(0))).containsExactly("quantity");
        assertThat(invalidPaths(new RestockRequest(100))).isEmpty();
        assertThat(invalidPaths(new PriceUpdateRequest(new BigDecimal("-2.00")))).containsExactly("unitPrice");
    }
}
