package com.retailops.orders.customer;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.validation.EmailValidator;
import com.retailops.schemas.Customer;
import com.retailops.schemas.CustomerTier;

@Service
public class CustomerService {

    private final CustomerRepository customerRepository;
    private final Clock clock;

    public CustomerService(CustomerRepository customerRepository, Clock clock) {
        this.customerRepository = customerRepository;
        this.clock = clock;
    }

    @Transactional
    public Customer create(CreateCustomerRequest request) {
        String email = EmailValidator.normalize(request.email());
        if (customerRepository.existsByEmailIgnoreCase(email)) {
            throw new DuplicateResourceException("Customer", email);
        }
        CustomerEntity entity = new CustomerEntity(UUID.randomUUID().toString(), request.name().trim(), email,
                request.tier(), request.region(), OffsetDateTime.now(clock));
        return CustomerMapper.toDto(customerRepository.save(entity));
    }

    @Transactional(readOnly = true)
    public Customer get(String id) {
        return CustomerMapper.toDto(find(id));
    }

    @Transactional(readOnly = true)
    public List<Customer> list(CustomerTier tier) {
        List<CustomerEntity> customers = tier == null
                ? customerRepository.findAllByOrderByNameAscIdAsc()
                : customerRepository.findByTierOrderByNameAscIdAsc(tier);
        return customers.stream().map(CustomerMapper::toDto).toList();
    }

    @Transactional
    public Customer changeTier(String id, CustomerTier tier) {
        CustomerEntity customer = find(id);
        customer.changeTier(tier);
        return CustomerMapper.toDto(customer);
    }

    private CustomerEntity find(String id) {
        return customerRepository.findById(id).orElseThrow(() -> new NotFoundException("Customer", id));
    }
}
