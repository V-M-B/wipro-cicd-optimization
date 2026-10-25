from __future__ import annotations

import random
from datetime import date

import pytest

from app import datasets
from app.datasets import DatasetConfig, generate_dataset, status_mix_for_age
from app.generated.schemas import Category, OrderStatus
from app.metrics.common import order_day, order_gross


def test_same_seed_gives_identical_data():
    a = generate_dataset(DatasetConfig(seed=11, n_orders=300))
    b = generate_dataset(DatasetConfig(seed=11, n_orders=300))
    assert [o.model_dump() for o in a.orders] == [o.model_dump() for o in b.orders]
    assert a.customers == b.customers
    assert a.products == b.products


def test_different_seeds_differ():
    a = generate_dataset(DatasetConfig(seed=1, n_orders=200))
    b = generate_dataset(DatasetConfig(seed=2, n_orders=200))
    assert [o.total for o in a.orders] != [o.total for o in b.orders]


def test_generation_does_not_touch_global_random_state():
    random.seed(1234)
    expected = random.random()
    random.seed(1234)
    generate_dataset(DatasetConfig(n_orders=50))
    assert random.random() == expected


@pytest.mark.parametrize(
    ("n_customers", "n_products", "n_orders"),
    [(1, 2, 0), (1, 2, 10), (10, 5, 100), (50, 25, 250), (300, 60, 900)],
)
def test_sizes_are_respected(n_customers, n_products, n_orders):
    ds = generate_dataset(DatasetConfig(n_customers=n_customers, n_products=n_products, n_orders=n_orders))
    assert len(ds.customers) == n_customers
    assert len(ds.products) == n_products
    assert len(ds.orders) == n_orders


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2025, 1, 1), date(2025, 1, 1)),
        (date(2025, 2, 1), date(2025, 2, 28)),
        (date(2024, 2, 1), date(2024, 3, 31)),
        (date(2023, 6, 15), date(2025, 6, 14)),
    ],
)
def test_order_dates_within_configured_range(start, end):
    ds = generate_dataset(DatasetConfig(start=start, end=end, n_orders=400))
    days = [order_day(o) for o in ds.orders]
    assert min(days) >= start
    assert max(days) <= end


def test_orders_sorted_chronologically_with_sequential_ids(small_dataset):
    created = [o.createdAt for o in small_dataset.orders]
    assert created == sorted(created)
    assert [o.id for o in small_dataset.orders] == [f"O{i:07d}" for i in range(1, len(created) + 1)]


def test_ids_are_unique(small_dataset):
    assert len({c.id for c in small_dataset.customers}) == len(small_dataset.customers)
    assert len({p.sku for p in small_dataset.products}) == len(small_dataset.products)
    assert len({o.id for o in small_dataset.orders}) == len(small_dataset.orders)


def test_orders_reference_known_customers_and_products(small_dataset):
    customer_ids = {c.id for c in small_dataset.customers}
    skus = {p.sku for p in small_dataset.products}
    for o in small_dataset.orders:
        assert o.customerId in customer_ids
        assert all(line.sku in skus for line in o.lines)


def test_order_lines_have_unique_skus_and_positive_quantities(small_dataset):
    for o in small_dataset.orders:
        assert o.lines
        assert len({line.sku for line in o.lines}) == len(o.lines)
        assert all(1 <= line.quantity <= 50 for line in o.lines)
        assert all(line.unitPrice > 0 for line in o.lines)


def test_totals_apply_coupon_discounts(small_dataset):
    for o in small_dataset.orders:
        discount = datasets.COUPONS[o.couponCode] if o.couponCode else 0.0
        assert o.total == pytest.approx(round(order_gross(o) * (1 - discount), 2), abs=0.005)


def test_coupon_rate_zero_means_no_coupons():
    ds = generate_dataset(DatasetConfig(coupon_rate=0.0, n_orders=300))
    assert all(o.couponCode is None for o in ds.orders)


def test_coupon_rate_one_means_all_coupons():
    ds = generate_dataset(DatasetConfig(coupon_rate=1.0, n_orders=200))
    assert all(o.couponCode in datasets.COUPONS for o in ds.orders)


def test_max_lines_one_limits_baskets_without_bundles():
    ds = generate_dataset(DatasetConfig(max_lines=1, bundle_rate=0.0, n_orders=300))
    assert all(len(o.lines) == 1 for o in ds.orders)


def test_bundles_pair_neighbouring_products():
    ds = generate_dataset(DatasetConfig(max_lines=1, bundle_rate=1.0, n_products=10, n_orders=200))
    index = {p.sku: i for i, p in enumerate(ds.products)}
    for o in ds.orders:
        positions = sorted(index[line.sku] for line in o.lines)
        assert len(positions) == 2
        assert positions[0] ^ 1 == positions[1]


def test_products_cycle_through_categories(small_dataset):
    categories = [p.category for p in small_dataset.products[: len(Category)]]
    assert categories == list(Category)


@pytest.mark.parametrize("category", list(Category))
def test_product_prices_within_category_range(small_dataset, category):
    low, high = datasets.PRICE_RANGES[category]
    prices = [p.unitPrice for p in small_dataset.products if p.category is category]
    assert prices
    assert all(low - 0.01 <= price <= high + 0.01 for price in prices)


def test_customer_emails_are_unique_and_well_formed(small_dataset):
    emails = [c.email for c in small_dataset.customers]
    assert len(set(emails)) == len(emails)
    assert all(e.endswith("@example.com") and e.count("@") == 1 for e in emails)


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, datasets.RECENT_STATUS_MIX),
        (2, datasets.RECENT_STATUS_MIX),
        (3, datasets.MID_STATUS_MIX),
        (11, datasets.MID_STATUS_MIX),
        (12, datasets.OLD_STATUS_MIX),
        (400, datasets.OLD_STATUS_MIX),
    ],
)
def test_status_mix_for_age(age, expected):
    assert status_mix_for_age(age) is expected


def test_recent_orders_are_never_delivered():
    config = DatasetConfig(n_orders=2_000, start=date(2025, 1, 1), end=date(2025, 3, 31))
    ds = generate_dataset(config)
    recent = [o for o in ds.orders if (config.end - order_day(o)).days < datasets.RECENT_AGE_DAYS]
    assert recent
    assert all(o.status in {OrderStatus.CREATED, OrderStatus.PAID, OrderStatus.CANCELLED} for o in recent)


def test_old_orders_are_mostly_delivered(small_dataset):
    old = [o for o in small_dataset.orders if (date(2025, 12, 31) - order_day(o)).days >= datasets.MID_AGE_DAYS]
    delivered = sum(o.status is OrderStatus.DELIVERED for o in old)
    assert delivered / len(old) > 0.8


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_customers": 0},
        {"n_products": 1},
        {"n_orders": -1},
        {"start": date(2025, 2, 1), "end": date(2025, 1, 31)},
        {"max_lines": 0},
        {"coupon_rate": 1.5},
        {"bundle_rate": -0.1},
    ],
)
def test_invalid_config_rejected(kwargs):
    with pytest.raises(ValueError):  # noqa: PT011 - message varies per field
        DatasetConfig(**kwargs)


def test_config_and_overrides_are_mutually_exclusive():
    with pytest.raises(TypeError):
        generate_dataset(DatasetConfig(), n_orders=5)


def test_overrides_build_config():
    ds = generate_dataset(n_orders=7, seed=3)
    assert ds.config == DatasetConfig(n_orders=7, seed=3)
    assert len(ds.orders) == 7


def test_span_days_inclusive():
    assert DatasetConfig(start=date(2025, 1, 1), end=date(2025, 1, 31)).span_days == 31


def test_indexes(small_dataset):
    assert small_dataset.customer_index()["C000001"] == small_dataset.customers[0]
    first = small_dataset.products[0]
    assert small_dataset.product_index()[first.sku] == first
