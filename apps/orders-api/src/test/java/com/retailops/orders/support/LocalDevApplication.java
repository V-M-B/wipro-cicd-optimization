package com.retailops.orders.support;

import org.springframework.boot.SpringApplication;

import com.retailops.orders.OrdersApiApplication;

/**
 * Runs the API locally against a throw-away Testcontainers PostgreSQL:
 * {@code ./mvnw spring-boot:test-run}.
 */
public class LocalDevApplication {

    public static void main(String[] args) {
        SpringApplication.from(OrdersApiApplication::main).with(PostgresTestcontainersConfig.class).run(args);
    }
}
