package com.retailops.orders.catalog;

import static org.hamcrest.Matchers.hasItems;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import com.retailops.orders.api.GlobalExceptionHandler;
import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.schemas.Category;
import com.retailops.schemas.Product;

@WebMvcTest(ProductController.class)
class ProductControllerTest {

    @Autowired
    MockMvc mvc;

    @MockitoBean
    ProductService productService;

    private final Product lamp = new Product("prd-27", "HOM-4003", "Desk Lamp", Category.HOME,
            new BigDecimal("27.75"), true);

    private static final String VALID_BODY = """
            {"sku":"HOM-4003","name":"Desk Lamp","category":"HOME","unitPrice":27.75,"initialStock":10}""";

    @Test
    void listReturnsProducts() throws Exception {
        when(productService.list(null, false)).thenReturn(List.of(lamp));
        mvc.perform(get("/api/products"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].sku").value("HOM-4003"))
                .andExpect(jsonPath("$[0].unitPrice").value(27.75))
                .andExpect(jsonPath("$[0].category").value("HOME"));
    }

    @Test
    void listPassesFilters() throws Exception {
        when(productService.list(Category.HOME, true)).thenReturn(List.of(lamp));
        mvc.perform(get("/api/products").param("category", "HOME").param("activeOnly", "true"))
                .andExpect(status().isOk());
        verify(productService).list(Category.HOME, true);
    }

    @Test
    void unknownCategoryIsBadRequest() throws Exception {
        mvc.perform(get("/api/products").param("category", "FOOD"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON));
        verifyNoInteractions(productService);
    }

    @Test
    void getBySku() throws Exception {
        when(productService.get("HOM-4003")).thenReturn(lamp);
        mvc.perform(get("/api/products/HOM-4003"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Desk Lamp"))
                .andExpect(jsonPath("$.active").value(true));
    }

    @Test
    void missingProductIsProblem404() throws Exception {
        when(productService.get("NOP-0001")).thenThrow(new NotFoundException("Product", "NOP-0001"));
        mvc.perform(get("/api/products/NOP-0001"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.type").value(GlobalExceptionHandler.TYPE_BASE + "not-found"))
                .andExpect(jsonPath("$.identifier").value("NOP-0001"))
                .andExpect(jsonPath("$.instance").value("/api/products/NOP-0001"));
    }

    @Test
    void createReturns201WithLocation() throws Exception {
        when(productService.create(any())).thenReturn(lamp);
        mvc.perform(post("/api/products").contentType(MediaType.APPLICATION_JSON).content(VALID_BODY))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/products/HOM-4003"))
                .andExpect(jsonPath("$.id").value("prd-27"));
    }

    @Test
    void invalidCreateListsFieldErrors() throws Exception {
        mvc.perform(post("/api/products").contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"sku":"lamp","name":"Desk Lamp","category":"HOME","unitPrice":0,"initialStock":1}"""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.type").value(GlobalExceptionHandler.TYPE_BASE + "validation-failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItems("sku", "unitPrice")));
        verifyNoInteractions(productService);
    }

    @Test
    void duplicateSkuIsConflict() throws Exception {
        when(productService.create(any())).thenThrow(new DuplicateResourceException("Product", "HOM-4003"));
        mvc.perform(post("/api/products").contentType(MediaType.APPLICATION_JSON).content(VALID_BODY))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.key").value("HOM-4003"));
    }

    @Test
    void updatePrice() throws Exception {
        when(productService.updatePrice("HOM-4003", new BigDecimal("29.99")))
                .thenReturn(new Product("prd-27", "HOM-4003", "Desk Lamp", Category.HOME, new BigDecimal("29.99"), true));
        mvc.perform(put("/api/products/HOM-4003/price").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"unitPrice\":29.99}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.unitPrice").value(29.99));
    }

    @Test
    void deactivate() throws Exception {
        when(productService.deactivate("HOM-4003"))
                .thenReturn(new Product("prd-27", "HOM-4003", "Desk Lamp", Category.HOME, new BigDecimal("27.75"), false));
        mvc.perform(post("/api/products/HOM-4003/deactivate"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.active").value(false));
    }
}
