Source: `experiments/results/tia-faults-20261025T173830Z.json` (repo HEAD `b17eecf2`)

| App | Faults | Detected by full suite | Not detected by any test | Not viable | Hybrid recall | Static-only recall | Mean share of test units selected (hybrid) | (static-only) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| analytics | 20 | 12 | 8 | 0 | 100.0% | 100.0% | 23.2% | 100.0% |
| orders-api | 20 | 17 | 3 | 0 | 100.0% | 100.0% | 36.2% | 45.6% |
| web | 20 | 15 | 5 | 0 | 100.0% | 100.0% | 31.2% | 77.6% |
| **all** | 60 | 44 | 16 | 0 | 100.0% | 100.0% | | |

Selection share is over each app's unit and integration test units (e2e excluded: always run in full on web source changes). Units: Java test classes, Vitest files, pytest modules.

**Misses (fault detected by the full suite but not by the selection):** none (hybrid); static-only: none.

### Per-fault detail

| Fault | Operator | File:line | Status | Failing units | Hybrid selected | Static selected |
|---|---|---|---|---:|---:|---:|
| orders-api-01 | logical | `PricingProperties.java:46` | undetected-by-suite | 0 | 24 – | 27 – |
| orders-api-02 | relational | `CouponRepository.java:15` | undetected-by-suite | 0 | 10 – | 20 – |
| orders-api-03 | relational | `PageResponse.java:21` | detected | 1 | 10 ✓ | 11 ✓ |
| orders-api-04 | relational | `QuantityRules.java:15` | detected | 7 | 12 ✓ | 14 ✓ |
| orders-api-05 | relational | `SkuValidator.java:22` | detected | 9 | 14 ✓ | 16 ✓ |
| orders-api-06 | relational | `InventoryService.java:61` | detected | 4 | 14 ✓ | 15 ✓ |
| orders-api-07 | logical | `OrderFilter.java:14` | detected | 4 | 10 ✓ | 14 ✓ |
| orders-api-08 | logical | `Coupon.java:28` | detected | 6 | 22 ✓ | 29 ✓ |
| orders-api-09 | boolean | `CouponEvaluator.java:45` | detected | 2 | 20 ✓ | 27 ✓ |
| orders-api-10 | logical | `StockLevel.java:9` | detected | 1 | 15 ✓ | 15 ✓ |
| orders-api-11 | negation | `CouponEvaluator.java:20` | detected | 5 | 20 ✓ | 27 ✓ |
| orders-api-12 | boolean | `CouponRepository.java:14` | detected | 1 | 10 ✓ | 20 ✓ |
| orders-api-13 | boolean | `EmailValidator.java:37` | undetected-by-suite | 0 | 11 – | 13 – |
| orders-api-14 | negation | `OrderLines.java:27` | detected | 6 | 10 ✓ | 14 ✓ |
| orders-api-15 | boolean | `CouponEvaluator.java:43` | detected | 2 | 20 ✓ | 27 ✓ |
| orders-api-16 | negation | `OrderStateMachine.java:48` | detected | 7 | 13 ✓ | 14 ✓ |
| orders-api-17 | boolean | `EmailValidator.java:24` | detected | 1 | 11 ✓ | 13 ✓ |
| orders-api-18 | logical | `ShippingPolicy.java:27` | detected | 4 | 22 ✓ | 27 ✓ |
| orders-api-19 | negation | `QuantityRules.java:19` | detected | 7 | 12 ✓ | 14 ✓ |
| orders-api-20 | negation | `EmailValidator.java:32` | detected | 4 | 11 ✓ | 13 ✓ |
| web-01 | constant | `cart.ts:8` | detected | 3 | 18 ✓ | 36 ✓ |
| web-02 | boolean | `csv.ts:63` | detected | 1 | 3 ✓ | 28 ✓ |
| web-03 | relational | `money.ts:23` | undetected-by-suite | 0 | 24 – | 37 – |
| web-04 | boolean | `dates.ts:9` | undetected-by-suite | 0 | 20 – | 38 – |
| web-05 | boolean | `orderQuery.ts:40` | detected | 1 | 12 ✓ | 33 ✓ |
| web-06 | logical | `orderQuery.ts:89` | detected | 3 | 12 ✓ | 33 ✓ |
| web-07 | logical | `cart.ts:96` | detected | 2 | 18 ✓ | 36 ✓ |
| web-08 | logical | `dates.ts:33` | detected | 1 | 20 ✓ | 38 ✓ |
| web-09 | negation | `format.ts:14` | detected | 11 | 13 ✓ | 37 ✓ |
| web-10 | logical | `orderQuery.ts:33` | detected | 3 | 12 ✓ | 33 ✓ |
| web-11 | relational | `orderStatus.ts:77` | detected | 1 | 17 ✓ | 36 ✓ |
| web-12 | boolean | `orderQuery.ts:47` | detected | 3 | 12 ✓ | 33 ✓ |
| web-13 | constant | `cart.ts:7` | detected | 3 | 18 ✓ | 36 ✓ |
| web-14 | relational | `api.ts:45` | undetected-by-suite | 0 | 10 – | 33 – |
| web-15 | negation | `validators.ts:80` | detected | 2 | 5 ✓ | 29 ✓ |
| web-16 | relational | `cart.ts:155` | undetected-by-suite | 0 | 18 – | 36 – |
| web-17 | logical | `orderQuery.ts:41` | detected | 1 | 12 ✓ | 33 ✓ |
| web-18 | relational | `api.ts:204` | undetected-by-suite | 0 | 10 – | 33 – |
| web-19 | negation | `cart.ts:82` | detected | 4 | 18 ✓ | 36 ✓ |
| web-20 | boolean | `search.ts:99` | detected | 2 | 16 ✓ | 35 ✓ |
| analytics-01 | constant | `datasets.py:193` | undetected-by-suite | 0 | 20 – | 33 – |
| analytics-02 | relational | `customers.py:145` | detected | 2 | 8 ✓ | 33 ✓ |
| analytics-03 | relational | `timeseries.py:196` | detected | 1 | 5 ✓ | 33 ✓ |
| analytics-04 | relational | `api.py:149` | detected | 1 | 8 ✓ | 33 ✓ |
| analytics-05 | relational | `datasets.py:243` | detected | 1 | 20 ✓ | 33 ✓ |
| analytics-06 | off-by-one | `datasets.py:238` | undetected-by-suite | 0 | 20 – | 33 – |
| analytics-07 | constant | `customers.py:285` | undetected-by-suite | 0 | 8 – | 33 – |
| analytics-08 | relational | `csv_io.py:107` | detected | 4 | 6 ✓ | 33 ✓ |
| analytics-09 | off-by-one | `timeseries.py:199` | detected | 2 | 5 ✓ | 33 ✓ |
| analytics-10 | logical | `csv_io.py:190` | detected | 5 | 6 ✓ | 33 ✓ |
| analytics-11 | logical | `csv_io.py:269` | detected | 2 | 6 ✓ | 33 ✓ |
| analytics-12 | negation | `customers.py:198` | detected | 3 | 8 ✓ | 33 ✓ |
| analytics-13 | logical | `csv_io.py:3` | undetected-by-suite | 0 | 6 – | 33 – |
| analytics-14 | logical | `funnel.py:4` | undetected-by-suite | 0 | 5 – | 33 – |
| analytics-15 | negation | `customers.py:204` | detected | 3 | 8 ✓ | 33 ✓ |
| analytics-16 | negation | `csv_io.py:134` | detected | 4 | 6 ✓ | 33 ✓ |
| analytics-17 | logical | `customers.py:196` | undetected-by-suite | 0 | 8 – | 33 – |
| analytics-18 | negation | `csv_io.py:141` | detected | 6 | 6 ✓ | 33 ✓ |
| analytics-19 | boolean | `csv_io.py:260` | undetected-by-suite | 0 | 6 – | 33 – |
| analytics-20 | constant | `datasets.py:239` | undetected-by-suite | 0 | 20 – | 33 – |

✓ selection contains a failing unit · ✗ miss · – no test detects the fault at all

### Faults no test detects (test-suite gaps)

- `orders-api-01` `apps/orders-api/src/main/java/com/retailops/orders/pricing/PricingProperties.java:46` (logical): `if (freeShippingThreshold.signum() < 0 || perUnitShippingSurcharge.sig` → `if (freeShippingThreshold.signum() < 0 || perUnitShippingSurcharge.sig`
- `orders-api-02` `apps/orders-api/src/main/java/com/retailops/orders/pricing/CouponRepository.java:15` (relational): `and (c.validFrom is null or c.validFrom <= :date)` → `and (c.validFrom is null or c.validFrom < :date)`
- `orders-api-13` `apps/orders-api/src/main/java/com/retailops/orders/validation/EmailValidator.java:37` (boolean): `return false;` → `return true;`
- `web-03` `apps/web/src/lib/money.ts:23` (relational): `if (Math.abs(diff - 0.5) < HALF_EPSILON) {` → `if (Math.abs(diff - 0.5) <= HALF_EPSILON) {`
- `web-04` `apps/web/src/lib/dates.ts:9` (boolean): `if (month < 1 || month > 12 || day < 1) return false;` → `if (month < 1 || month > 12 || day < 1) return true;`
- `web-14` `apps/web/src/lib/api.ts:45` (relational): `if (status >= 500 && status <= 599) return 'server';` → `if (status >= 500 && status < 599) return 'server';`
- `web-16` `apps/web/src/lib/cart.ts:155` (relational): `if (amount <= 0) return 0;` → `if (amount < 0) return 0;`
- `web-18` `apps/web/src/lib/api.ts:204` (relational): `for (let attempt = 0; attempt < maxAttempts; attempt += 1) {` → `for (let attempt = 0; attempt <= maxAttempts; attempt += 1) {`
- `analytics-01` `apps/analytics/app/datasets.py:193` (constant): `active=rng.random() > 0.05,` → `active=rng.random() > 0.06,`
- `analytics-06` `apps/analytics/app/datasets.py:238` (off-by-one): `pi = min(bisect.bisect_left(cum_popularity, rng.random() * total_popul` → `pi = min(bisect.bisect_left(cum_popularity, rng.random() * total_popul`
- `analytics-07` `apps/analytics/app/metrics/customers.py:285` (constant): `discount_rate: float = 0.01,` → `discount_rate: float = 0.02,`
- `analytics-13` `apps/analytics/app/io/csv_io.py:3` (logical): `Readers collect *all* row errors (up to ``max_errors``) and raise a si` → `Readers collect *all* row errors (up to ``max_errors``) or raise a sin`
- `analytics-14` `apps/analytics/app/metrics/funnel.py:4` (logical): `passed through CREATED, PAID and SHIPPED. CANCELLED orders are assumed` → `passed through CREATED, PAID or SHIPPED. CANCELLED orders are assumed `
- `analytics-17` `apps/analytics/app/metrics/customers.py:196` (logical): `Columns run up to the last month with data (or ``end``), so the matrix` → `Columns run up to the last month with data (and ``end``), so the matri`
- `analytics-19` `apps/analytics/app/io/csv_io.py:260` (boolean): `for fname, a, b in zip(ORDER_HEADER_FIELDS, first_raw, header_raw, str` → `for fname, a, b in zip(ORDER_HEADER_FIELDS, first_raw, header_raw, str`
- `analytics-20` `apps/analytics/app/datasets.py:239` (constant): `quantities[pi] = quantities.get(pi, 0) + 1 + min(9, int(rng.expovariat` → `quantities[pi] = quantities.get(pi, 0) + 1 + min(9, int(rng.expovariat`
