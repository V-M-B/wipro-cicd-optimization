package com.retailops.orders.customer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.retailops.orders.common.DuplicateResourceException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.Customer;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

@ExtendWith(MockitoExtension.class)
class CustomerServiceTest {

    @Mock
    CustomerRepository repository;

    CustomerService service;

    @BeforeEach
    void setUp() {
        service = new CustomerService(repository, TestFixtures.fixedClock());
    }

    private static CustomerEntity entity(String id, String name, CustomerTier tier) {
        return new CustomerEntity(id, name, id + "@example.com", tier, Region.EAST, TestFixtures.NOW_UTC);
    }

    @Test
    void duplicateEmailIsDetectedCaseInsensitively() {
        when(repository.existsByEmailIgnoreCase("asha@example.com")).thenReturn(true);
        assertThatThrownBy(() -> service.create(new CreateCustomerRequest("Asha", " ASHA@Example.com ",
                CustomerTier.GOLD, Region.NORTH))).isInstanceOf(DuplicateResourceException.class);
        verify(repository, never()).save(any());
    }

    @Test
    void createStoresNormalisedValues() {
        when(repository.existsByEmailIgnoreCase("asha@example.com")).thenReturn(false);
        when(repository.save(any(CustomerEntity.class))).thenAnswer(inv -> inv.getArgument(0));
        Customer customer = service.create(new CreateCustomerRequest("  Asha Rao ", "Asha@Example.com",
                CustomerTier.GOLD, Region.NORTH));
        assertThat(customer.name()).isEqualTo("Asha Rao");
        assertThat(customer.email()).isEqualTo("asha@example.com");
        assertThat(customer.tier()).isEqualTo(CustomerTier.GOLD);
        assertThat(customer.id()).isNotBlank();
    }

    @Test
    void getMissingIsNotFound() {
        when(repository.findById("cus-x")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.get("cus-x")).isInstanceOf(NotFoundException.class);
    }

    @Test
    void listWithoutTierReturnsEveryone() {
        when(repository.findAllByOrderByNameAscIdAsc())
                .thenReturn(List.of(entity("c1", "Ann", CustomerTier.GOLD), entity("c2", "Bob", CustomerTier.SILVER)));
        assertThat(service.list(null)).extracting(Customer::name).containsExactly("Ann", "Bob");
    }

    @Test
    void listByTier() {
        when(repository.findByTierOrderByNameAscIdAsc(CustomerTier.GOLD))
                .thenReturn(List.of(entity("c1", "Ann", CustomerTier.GOLD)));
        assertThat(service.list(CustomerTier.GOLD)).extracting(Customer::id).containsExactly("c1");
    }

    @Test
    void changeTierUpdatesEntity() {
        CustomerEntity stored = entity("c1", "Ann", CustomerTier.SILVER);
        when(repository.findById("c1")).thenReturn(Optional.of(stored));
        assertThat(service.changeTier("c1", CustomerTier.PLATINUM).tier()).isEqualTo(CustomerTier.PLATINUM);
        assertThat(stored.getTier()).isEqualTo(CustomerTier.PLATINUM);
    }
}
