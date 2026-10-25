package com.retailops.orders.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;

import jakarta.persistence.EntityManagerFactory;

import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationInfo;
import org.flywaydb.core.api.MigrationState;
import org.flywaydb.core.api.output.MigrateResult;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;

import com.retailops.orders.support.PostgresTestcontainersConfig;

/** Verifies the Flyway history, schema objects and seed data on a fresh PostgreSQL. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE, properties = "spring.flyway.clean-disabled=false")
@Import(PostgresTestcontainersConfig.class)
class FlywayMigrationIT {

    @Autowired
    Flyway flyway;
    @Autowired
    JdbcTemplate jdbc;
    @Autowired
    EntityManagerFactory entityManagerFactory;

    private long count(String table) {
        return jdbc.queryForObject("select count(*) from " + table, Long.class);
    }

    @Test
    void allMigrationsAppliedSuccessfully() {
        MigrationInfo[] applied = flyway.info().applied();
        assertThat(Arrays.stream(applied).map(m -> m.getVersion().getVersion())).containsExactly("1", "2", "3");
        assertThat(applied).allMatch(m -> m.getState() == MigrationState.SUCCESS);
        assertThat(flyway.info().pending()).isEmpty();
        assertThat(flyway.validateWithResult().validationSuccessful).isTrue();
    }

    @Test
    void seedDataIsPresent() {
        assertThat(count("products")).isEqualTo(40);
        assertThat(count("stock_items")).isEqualTo(40);
        assertThat(count("customers")).isEqualTo(12);
        assertThat(count("coupons")).isEqualTo(7);
    }

    @Test
    void expectedTablesAndIndexesExist() {
        assertThat(jdbc.queryForList("select table_name from information_schema.tables where table_schema = 'public'",
                String.class)).contains("products", "customers", "stock_items", "coupons", "orders", "order_lines",
                "flyway_schema_history");
        assertThat(jdbc.queryForList("select indexname from pg_indexes where schemaname = 'public'", String.class))
                .contains("idx_orders_customer_created", "idx_orders_status", "idx_order_lines_order",
                        "idx_order_lines_sku", "idx_products_category");
    }

    @Test
    void stockConstraintRejectsOverReservation() {
        assertThatThrownBy(() -> jdbc.update("update stock_items set reserved = on_hand + 1 where sku = 'ELE-1001'"))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void hibernateMappingMatchesMigratedSchema() {
        // ddl-auto=validate already ran at startup; also confirm every entity is mapped.
        assertThat(entityManagerFactory.getMetamodel().getEntities()).hasSize(6);
    }

    @Test
    void cleanAndMigrateIsRepeatable() {
        flyway.clean();
        MigrateResult result = flyway.migrate();
        assertThat(result.migrationsExecuted).isEqualTo(3);
        assertThat(count("products")).isEqualTo(40);
        assertThat(count("orders")).isZero();
    }
}
