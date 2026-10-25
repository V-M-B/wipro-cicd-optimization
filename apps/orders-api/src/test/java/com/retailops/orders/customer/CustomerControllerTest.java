package com.retailops.orders.customer;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
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
import com.retailops.schemas.Customer;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

@WebMvcTest(CustomerController.class)
class CustomerControllerTest {

    @Autowired
    MockMvc mvc;

    @MockitoBean
    CustomerService customerService;

    private final Customer grace = new Customer("cus-0007", "Grace Kim", "grace.kim@example.com", CustomerTier.GOLD,
            Region.EAST);

    @Test
    void createReturns201() throws Exception {
        when(customerService.create(any())).thenReturn(grace);
        mvc.perform(post("/api/customers").contentType(MediaType.APPLICATION_JSON).content("""
                        {"name":"Grace Kim","email":"grace.kim@example.com","tier":"GOLD","region":"EAST"}"""))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/customers/cus-0007"))
                .andExpect(jsonPath("$.tier").value("GOLD"));
    }

    @Test
    void invalidEmailIsRejected() throws Exception {
        mvc.perform(post("/api/customers").contentType(MediaType.APPLICATION_JSON).content("""
                        {"name":"Grace Kim","email":"grace@","tier":"GOLD","region":"EAST"}"""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("email"));
        verifyNoInteractions(customerService);
    }

    @Test
    void unknownEnumValueInBodyIsBadRequest() throws Exception {
        mvc.perform(post("/api/customers").contentType(MediaType.APPLICATION_JSON).content("""
                        {"name":"Grace Kim","email":"grace@example.com","tier":"DIAMOND","region":"EAST"}"""))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(customerService);
    }

    @Test
    void malformedJsonIsBadRequest() throws Exception {
        mvc.perform(post("/api/customers").contentType(MediaType.APPLICATION_JSON).content("{\"name\":"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void getMissingIs404() throws Exception {
        when(customerService.get("cus-x")).thenThrow(new NotFoundException("Customer", "cus-x"));
        mvc.perform(get("/api/customers/cus-x"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.resource").value("Customer"));
    }

    @Test
    void listByTier() throws Exception {
        when(customerService.list(CustomerTier.GOLD)).thenReturn(List.of(grace));
        mvc.perform(get("/api/customers").param("tier", "GOLD"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value("cus-0007"));
        verify(customerService).list(CustomerTier.GOLD);
    }

    @Test
    void changeTier() throws Exception {
        when(customerService.changeTier("cus-0007", CustomerTier.PLATINUM)).thenReturn(
                new Customer("cus-0007", "Grace Kim", "grace.kim@example.com", CustomerTier.PLATINUM, Region.EAST));
        mvc.perform(put("/api/customers/cus-0007/tier").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"tier\":\"PLATINUM\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.tier").value("PLATINUM"));
    }
}
