package com.retailops.orders.customer;

import java.net.URI;
import java.util.List;

import jakarta.validation.Valid;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.retailops.schemas.Customer;
import com.retailops.schemas.CustomerTier;

@RestController
@RequestMapping("/api/customers")
public class CustomerController {

    private final CustomerService customerService;

    public CustomerController(CustomerService customerService) {
        this.customerService = customerService;
    }

    @PostMapping
    public ResponseEntity<Customer> create(@Valid @RequestBody CreateCustomerRequest request) {
        Customer created = customerService.create(request);
        return ResponseEntity.created(URI.create("/api/customers/" + created.id())).body(created);
    }

    @GetMapping("/{id}")
    public Customer get(@PathVariable String id) {
        return customerService.get(id);
    }

    @GetMapping
    public List<Customer> list(@RequestParam(required = false) CustomerTier tier) {
        return customerService.list(tier);
    }

    @PutMapping("/{id}/tier")
    public Customer changeTier(@PathVariable String id, @Valid @RequestBody TierChangeRequest request) {
        return customerService.changeTier(id, request.tier());
    }
}
