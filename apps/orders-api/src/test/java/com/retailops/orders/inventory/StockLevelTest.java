package com.retailops.orders.inventory;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import com.retailops.schemas.InventoryLevel;

class StockLevelTest {

    @ParameterizedTest(name = "onHand={0} reserved={1} -> available {2}")
    @CsvSource({"10, 0, 10", "10, 3, 7", "10, 10, 0"})
    void availableIsOnHandMinusReserved(int onHand, int reserved, int available) {
        assertThat(new StockLevel("SKU-0001", onHand, reserved).available()).isEqualTo(available);
    }

    @ParameterizedTest(name = "request {0} from 7 available -> {1}")
    @CsvSource({"7, true", "8, false", "0, false"})
    void canFulfil(int quantity, boolean expected) {
        assertThat(new StockLevel("SKU-0001", 10, 3).canFulfil(quantity)).isEqualTo(expected);
    }

    @Test
    void convertsToTheSharedSchema() {
        assertThat(new StockLevel("ELE-1001", 10, 3).toSchema())
                .isEqualTo(new InventoryLevel("ELE-1001", 10, 3, 7));
    }

    @Test
    void outOfStockWhenNothingAvailable() {
        assertThat(new StockLevel("SKU-0001", 4, 4).isOutOfStock()).isTrue();
        assertThat(new StockLevel("SKU-0001", 4, 3).isOutOfStock()).isFalse();
    }

    @Test
    void negativeQuantitiesAreRejected() {
        assertThatThrownBy(() -> new StockLevel("SKU-0001", -1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new StockLevel("SKU-0001", 1, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void reservedCannotExceedOnHand() {
        assertThatThrownBy(() -> new StockLevel("SKU-0001", 2, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
