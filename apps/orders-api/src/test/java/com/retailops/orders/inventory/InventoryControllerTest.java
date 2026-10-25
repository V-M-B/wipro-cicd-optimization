package com.retailops.orders.inventory;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import com.retailops.orders.common.NotFoundException;

@WebMvcTest(InventoryController.class)
class InventoryControllerTest {

    @Autowired
    MockMvc mvc;

    @MockitoBean
    InventoryService inventoryService;

    @Test
    void levelIncludesAvailable() throws Exception {
        when(inventoryService.level("ELE-1001")).thenReturn(new StockLevel("ELE-1001", 10, 3));
        mvc.perform(get("/api/inventory/ELE-1001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.onHand").value(10))
                .andExpect(jsonPath("$.reserved").value(3))
                .andExpect(jsonPath("$.available").value(7));
    }

    @Test
    void unknownSkuIs404() throws Exception {
        when(inventoryService.level("NOP-0000")).thenThrow(new NotFoundException("Stock", "NOP-0000"));
        mvc.perform(get("/api/inventory/NOP-0000")).andExpect(status().isNotFound());
    }

    @Test
    void restock() throws Exception {
        when(inventoryService.restock("ELE-1001", 50)).thenReturn(new StockLevel("ELE-1001", 60, 3));
        mvc.perform(post("/api/inventory/ELE-1001/restock").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"quantity\":50}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.onHand").value(60));
    }

    @Test
    void restockOfZeroIsRejected() throws Exception {
        mvc.perform(post("/api/inventory/ELE-1001/restock").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"quantity\":0}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("quantity"));
        verifyNoInteractions(inventoryService);
    }

    @Test
    void lowStockDefaultsThresholdToTen() throws Exception {
        when(inventoryService.lowStock(10)).thenReturn(List.of(new StockLevel("ELE-1008", 0, 0)));
        mvc.perform(get("/api/inventory/low-stock"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].sku").value("ELE-1008"));
        verify(inventoryService).lowStock(10);
    }

    @Test
    void negativeThresholdIsRejected() throws Exception {
        mvc.perform(get("/api/inventory/low-stock").param("threshold", "-1")).andExpect(status().isBadRequest());
        verifyNoInteractions(inventoryService);
    }
}
