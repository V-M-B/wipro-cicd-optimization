# orders-api

RetailOps orders service: Java 21, Spring Boot 3.5.16, Spring Data JPA, Flyway, PostgreSQL.
It covers the product catalog, customers, inventory reservations, order pricing and the order
lifecycle. Its test suite is deliberately large and split across many classes, because the
CI-optimisation phases profile, shard and impact-analyse it.

## Layout

```
src/main/java/com/retailops/
  schemas/            generated DTOs (libs/shared-schemas/codegen.py), do not edit
  orders/
    api/              GlobalExceptionHandler (RFC 7807 problem details), PageResponse
    catalog/          ProductEntity/Repository/Service/Controller, ProductMapper
    customer/         CustomerEntity/Repository/Service/Controller, CustomerMapper
    inventory/        StockItemEntity, StockRepository (atomic conditional UPDATEs), InventoryService, StockLevel
    order/            OrderEntity/OrderLineEntity, OrderStateMachine, OrderService, OrderController, OrderFilter
    pricing/          PricingService + Tier/Bulk/Tax/Shipping policies, CouponEvaluator, QuoteService, PricingProperties
    validation/       SKU / e-mail / quantity validators and @ValidSku/@ValidEmail/@ValidQuantity
    common/, config/  exceptions, Clock bean
src/main/resources/db/migration/  V1 schema, V2 indexes, V3 seed data (40 products, 12 customers, 7 coupons)
scripts/generate_pricing_cases.py  test-data generator (see "Generated tests")
```

## Domain rules

**Order lifecycle.** `CREATED -> PAID -> SHIPPED -> DELIVERED`, plus `CREATED -> CANCELLED` and
`PAID -> CANCELLED`. Every other transition, including self-transitions, is rejected with HTTP 409.
Creating an order reserves stock. Cancelling releases the reservation, and shipping takes the
reserved units off on-hand stock. Stock changes are single conditional `UPDATE` statements, so
concurrent requests cannot oversell. Orders carry a JPA `@Version` field, so two concurrent
transitions of the same order cannot both succeed.

**Pricing** (`PricingService`): every amount is a `BigDecimal` rounded HALF_EVEN to 2 decimal places.
1. Line subtotal = unit price x quantity. The subtotal is the sum of the line subtotals.
2. Bulk discount on each line by its quantity: 10+ units 2%, 20+ 5%, 50+ 8%, 100+ 12%.
3. Tier discount on (subtotal - bulk): STANDARD 0%, SILVER 5%, GOLD 10%, PLATINUM 15%.
4. Coupon on what remains after step 3. A coupon is a PERCENTAGE (optional `maxDiscount` cap), a
   FIXED_AMOUNT (never more than the remaining amount) or FREE_SHIPPING. Minimum spend is checked
   against the subtotal. Validity dates are inclusive. A coupon can be rejected as UNKNOWN,
   INACTIVE, NOT_YET_VALID, EXPIRED or MIN_SPEND_NOT_MET (HTTP 422).
5. Tax on the net merchandise amount, by region: NORTH 8%, SOUTH 6.5%, EAST 7.25%, WEST 9%.
6. Shipping is free when the net amount is at least 75.00, for PLATINUM customers, or with a
   FREE_SHIPPING coupon. Otherwise it is the regional base rate (NORTH 5.99, SOUTH 4.99, EAST 5.49,
   WEST 6.99) plus 0.50 for each unit beyond the fifth.
7. Total = net + tax + shipping.

The threshold, tax rates, shipping rates and surcharge can be configured under `orders.pricing.*`
(bound to `PricingProperties`). Unset values fall back to the defaults above, and the two region maps
are merged over the defaults, so overriding one region leaves the others unchanged:

| Property | Default | Example override |
|---|---|---|
| `orders.pricing.free-shipping-threshold` | `75.00` | `orders.pricing.free-shipping-threshold=500.00` |
| `orders.pricing.tax-rates.<REGION>` | NORTH `0.0800`, SOUTH `0.0650`, EAST `0.0725`, WEST `0.0900` | `orders.pricing.tax-rates.WEST=0.1000` |
| `orders.pricing.shipping-base-rates.<REGION>` | NORTH `5.99`, SOUTH `4.99`, EAST `5.49`, WEST `6.99` | `orders.pricing.shipping-base-rates.NORTH=9.99` |
| `orders.pricing.per-unit-shipping-surcharge` | `0.50` | `orders.pricing.per-unit-shipping-surcharge=0.75` |
| `orders.pricing.surcharge-free-units` | `5` | `orders.pricing.surcharge-free-units=3` |

Negative values are rejected at startup. `PricingConfigurationIT` boots the application with the
first three example overrides and checks that quotes use them.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/products?category=&activeOnly=` | list, sorted by SKU |
| GET | `/api/products/{sku}` | |
| POST | `/api/products` | `{sku,name,category,unitPrice,initialStock}` -> 201 + Location |
| PUT | `/api/products/{sku}/price` | `{unitPrice}` |
| POST | `/api/products/{sku}/deactivate` | |
| GET | `/api/customers?tier=` / `/api/customers/{id}` | |
| POST | `/api/customers` | `{name,email,tier,region}`; e-mail unique (case-insensitive) |
| PUT | `/api/customers/{id}/tier` | `{tier}` |
| GET | `/api/inventory/{sku}` | `{sku,onHand,reserved,available}` |
| GET | `/api/inventory/low-stock?threshold=10` | |
| POST | `/api/inventory/{sku}/restock` | `{quantity}` |
| POST | `/api/orders` | `{customerId,lines:[{sku,quantity}],couponCode?}` -> 201; reserves stock |
| POST | `/api/orders/quote` | same body -> `PriceQuote {subtotal,discount,tax,shipping,total}` |
| GET | `/api/orders/{id}` | |
| GET | `/api/orders?customerId=&status=&from=&to=&page=0&size=20` | newest first; `size` <= 100; `from` inclusive, `to` exclusive (ISO-8601) |
| POST | `/api/orders/{id}/transitions` | `{target}` |
| GET | `/actuator/health` | |

Errors are `application/problem+json`, with `type` = `https://retailops.example/problems/<slug>`.
The slugs are `not-found`, `duplicate-resource`, `validation-failed` (with an `errors[]` array),
`illegal-status-transition` (with `allowed[]`), `insufficient-stock`, `coupon-rejected`,
`business-rule-violation` and `concurrent-modification`.

## Running

```bash
# build + all tests (Docker must be running for the Testcontainers integration tests)
./mvnw -B verify            # Windows: mvnw.cmd -B verify   (JAVA_HOME must point to a JDK 21)

# run against your own PostgreSQL (defaults: localhost:5432/orders, user/password orders)
SPRING_DATASOURCE_URL=jdbc:postgresql://host:5432/orders ./mvnw spring-boot:run

# run against a throw-away Testcontainers PostgreSQL
./mvnw spring-boot:test-run

# container image
docker build -t orders-api:local .
docker run -p 8080:8080 -e SPRING_DATASOURCE_URL=jdbc:postgresql://<db-host>:5432/orders orders-api:local
```

The Dockerfile copies the whole source tree before it builds, so every change downloads all the
dependencies again. This is intentional: it is the unoptimised baseline, and a later phase fixes the
layer ordering.

## Tests

`mvn verify` runs the unit tests with Surefire (`*Test.java`, reports in `target/surefire-reports`)
and the integration tests with Failsafe (`*IT.java`, reports in `target/failsafe-reports`). JaCoCo
writes `target/site/jacoco` (unit) and `target/site/jacoco-it` (integration).

The counts below are from the JUnit XML reports of the run on 2026-10-25. A parameterized
invocation counts as one test.

| Suite | Classes | Tests |
|---|---|---|
| Unit (`*Test`) | 33 | 375 |
| Integration (`*IT`, Testcontainers `postgres:16-alpine`) | 7 | 45 |
| **Total** | 40 | **420** |

The unit tests are mostly plain JUnit 5 + AssertJ (pricing policies, coupon rules, the exhaustive
25-pair state-machine check, validators, mappers), Mockito service tests, and four `@WebMvcTest`
controller slices with mocked services.

There are seven integration-test classes, and they use six different Spring context
configurations on purpose, so several Spring contexts and PostgreSQL containers start during a run:

| IT class | Context |
|---|---|
| `RepositoryQueriesIT` | `@DataJpaTest` slice, rolled back per test |
| `OrderLifecycleHttpIT`, `ProductCatalogHttpIT` | `@SpringBootTest(RANDOM_PORT)`, shared cached context |
| `OrderPaginationIT` | `@SpringBootTest` + MockMvc + a deterministic stepping `Clock` |
| `ConcurrentStockReservationIT` | `@SpringBootTest(NONE)`, 8 to 40 concurrent threads |
| `PricingConfigurationIT` | `@SpringBootTest(NONE)` with overridden `orders.pricing.*` |
| `FlywayMigrationIT` | `@SpringBootTest(NONE)` with `spring.flyway.clean-disabled=false` |

No test uses `Thread.sleep`. The time the suite takes comes from Spring context startup,
container startup and database work.

### Generated tests

`scripts/generate_pricing_cases.py` (fixed seed `20251025`) contains its own Python `decimal`
implementation of the pricing rules above, written separately from the Java code. It writes two CSV
files, and `@CsvFileSource` tests run every row through the real Java classes:

| Data file | Rows | Test class | What it checks |
|---|---|---|---|
| `src/test/resources/generated/pricing-scenarios.csv` | 24 (7 expect a coupon rejection) | `GeneratedPricingScenariosTest` | full `PriceBreakdown`, or the rejection reason |
| `src/test/resources/generated/shipping-matrix.csv` | 24 (4 regions x units {1,6,13} x net {74.99, 75.00}) | `GeneratedShippingMatrixTest` | `ShippingPolicy.cost` |

That gives **48 generated test invocations** out of the 375 unit tests. All other tests are written
by hand. To regenerate the data, run `python scripts/generate_pricing_cases.py [--scenarios N]`.

### Local timings

These are ad-hoc measurements on the development laptop, not CI baseline numbers. The machine was
Windows 11 with Docker Desktop 28.1.1 and Temurin 21.0.12. `~/.m2` was already populated and the
`postgres:16-alpine` image was already pulled. Each run started with `target/` deleted.

| Command | Wall clock |
|---|---|
| `./mvnw -B verify`, run 1 | 99 s (Maven "Total time" 01:28 min) |
| `./mvnw -B verify`, run 2 | 102 s (Maven "Total time" 01:38 min) |
| `docker build -t orders-api:local apps/orders-api` (base images not cached; includes pulls and the full dependency download inside the build) | 279 s |

In run 2, the test-class times summed from the XML reports were 19.5 s for unit tests and 55.0 s for
integration tests. The slowest classes were `ProductCatalogHttpIT` at 27.9 s and
`ProductControllerTest` at 11.9 s. Each of those runs first in its JVM, so it also pays for the first
Spring context startup, and `ProductCatalogHttpIT` also pays for the first container startup.
