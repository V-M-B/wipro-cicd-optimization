package com.retailops.orders.support;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * PostgreSQL via Testcontainers. The container is a bean, so every distinct Spring test context
 * gets its own database (contexts with identical configuration are cached and share it).
 */
@TestConfiguration(proxyBeanMethods = false)
public class PostgresTestcontainersConfig {

    public static final DockerImageName IMAGE = DockerImageName.parse("postgres:16-alpine");

    @Bean
    @ServiceConnection
    PostgreSQLContainer<?> postgresContainer() {
        return new PostgreSQLContainer<>(IMAGE);
    }
}
