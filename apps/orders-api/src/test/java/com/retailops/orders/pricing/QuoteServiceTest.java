package com.retailops.orders.pricing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.TreeMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.retailops.orders.catalog.ProductEntity;
import com.retailops.orders.catalog.ProductRepository;
import com.retailops.orders.common.BusinessRuleException;
import com.retailops.orders.common.NotFoundException;
import com.retailops.orders.customer.CustomerEntity;
import com.retailops.orders.customer.CustomerRepository;
import com.retailops.orders.support.TestFixtures;
import com.retailops.schemas.Category;
import com.retailops.schemas.CustomerTier;
import com.retailops.schemas.Region;

@ExtendWith(MockitoExtension.class)
class QuoteServiceTest {

    @Mock
    CustomerRepository customerRepository;
    @Mock
    ProductRepository productRepository;
    @Mock
    CouponRepository couponRepository;

    QuoteService quoteService;

    private final CustomerEntity gold = new CustomerEntity("cus-1", "Gold Buyer", "gold@example.com",
            CustomerTier.GOLD, Region.WEST, TestFixtures.NOW_UTC);

    @BeforeEach
    void setUp() {
        quoteService = new QuoteService(customerRepository, productRepository, couponRepository,
                TestFixtures.defaultPricingService());
    }

    private static ProductEntity product(String sku, String price) {
        return new ProductEntity("id-" + sku, sku, "Product " + sku, Category.HOME, new BigDecimal(price),
                TestFixtures.NOW_UTC);
    }

    private static TreeMap<String, Integer> quantities(Object... skuQty) {
        TreeMap<String, Integer> map = new TreeMap<>();
        for (int i = 0; i < skuQty.length; i += 2) {
            map.put((String) skuQty[i], (Integer) skuQty[i + 1]);
        }
        return map;
    }

    @Test
    void pricesWithCustomerTierAndRegion() {
        when(customerRepository.findById("cus-1")).thenReturn(Optional.of(gold));
        when(productRepository.findBySkuIn(anyCollection()))
                .thenReturn(List.of(product("GRO-2003", "8.45")));
        PricedOrder priced = quoteService.price("cus-1", quantities("GRO-2003", 10), null);
        assertThat(priced.tier()).isEqualTo(CustomerTier.GOLD);
        assertThat(priced.region()).isEqualTo(Region.WEST);
        assertThat(priced.breakdown().total()).isEqualTo(new BigDecimal("90.73"));
        assertThat(priced.couponCode()).isNull();
    }

    @Test
    void linesFollowSkuOrderOfRequest() {
        when(customerRepository.findById("cus-1")).thenReturn(Optional.of(gold));
        when(productRepository.findBySkuIn(anyCollection()))
                .thenReturn(List.of(product("TOY-5001", "44.99"), product("APP-3001", "14.99")));
        PricedOrder priced = quoteService.price("cus-1", quantities("TOY-5001", 1, "APP-3001", 2), null);
        assertThat(priced.lines()).extracting(PricedLine::sku).containsExactly("APP-3001", "TOY-5001");
    }

    @Test
    void unknownCustomerIsNotFound() {
        when(customerRepository.findById("nope")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> quoteService.price("nope", quantities("GRO-2003", 1), null))
                .isInstanceOf(NotFoundException.class).hasMessageContaining("Customer");
    }

    @Test
    void unknownProductIsNotFound() {
        when(customerRepository.findById("cus-1")).thenReturn(Optional.of(gold));
        when(productRepository.findBySkuIn(anyCollection())).thenReturn(List.of());
        assertThatThrownBy(() -> quoteService.price("cus-1", quantities("ZZZ-9999", 1), null))
                .isInstanceOfSatisfying(NotFoundException.class,
                        ex -> assertThat(ex.getIdentifier()).isEqualTo("ZZZ-9999"));
    }

    @Test
    void inactiveProductIsRejected() {
        ProductEntity retired = product("TOY-5008", "2.50");
        retired.deactivate();
        when(customerRepository.findById("cus-1")).thenReturn(Optional.of(gold));
        when(productRepository.findBySkuIn(anyCollection())).thenReturn(List.of(retired));
        assertThatThrownBy(() -> quoteService.price("cus-1", quantities("TOY-5008", 1), null))
                .isInstanceOfSatisfying(BusinessRuleException.class,
                        ex -> assertThat(ex.getCode()).isEqualTo("PRODUCT_INACTIVE"));
    }

    @Test
    void couponCodeIsNormalisedBeforeLookup() {
        when(couponRepository.findById("WELCOME10"))
                .thenReturn(Optional.of(new CouponEntity(Coupon.percentage("WELCOME10", "10"))));
        assertThat(quoteService.resolveCoupon("  welcome10 ").code()).isEqualTo("WELCOME10");
    }

    @Test
    void unknownCouponIsRejected() {
        when(couponRepository.findById("NOPE")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> quoteService.resolveCoupon("nope"))
                .isInstanceOfSatisfying(CouponRejectedException.class,
                        ex -> assertThat(ex.getReason()).isEqualTo(CouponRejectionReason.UNKNOWN));
    }

    @Test
    void blankCouponMeansNoCoupon() {
        assertThat(quoteService.resolveCoupon("   ")).isNull();
        assertThat(quoteService.resolveCoupon(null)).isNull();
    }
}
