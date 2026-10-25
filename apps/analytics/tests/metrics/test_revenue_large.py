"""Data-heavy revenue invariants over a 100k-order generated dataset."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import pytest

from app.datasets import COUPONS
from app.metrics import revenue
from tests.factories import large_dataset

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def big():
    return large_dataset(100_000, seed=101)


@pytest.fixture(scope="module")
def total(big):
    return revenue.total_revenue(big.orders)


def test_region_breakdown_reconciles(big, total):
    by_region = revenue.revenue_by_region(big.orders, big.customers)
    assert set(by_region) == {"NORTH", "SOUTH", "EAST", "WEST"}
    assert sum(by_region.values()) == pytest.approx(total, abs=0.05)


def test_category_breakdown_reconciles(big, total):
    by_category = revenue.revenue_by_category(big.orders, big.products)
    assert set(by_category) == {"ELECTRONICS", "GROCERY", "APPAREL", "HOME", "TOYS"}
    assert sum(by_category.values()) == pytest.approx(total, abs=0.05)


@pytest.mark.parametrize("granularity", ["day", "week", "month"])
def test_period_breakdowns_reconcile(big, total, granularity):
    by_period = revenue.revenue_by_period(big.orders, granularity)
    assert sum(by_period.values()) == pytest.approx(total, abs=0.01 * len(by_period))


def test_monthly_equals_sum_of_daily(big):
    daily = revenue.revenue_by_period(big.orders, "day")
    monthly = revenue.revenue_by_period(big.orders, "month")
    rolled: dict[str, float] = defaultdict(float)
    for day, value in daily.items():
        rolled[day[:7]] += value
    assert set(rolled) == set(monthly)
    for month, value in monthly.items():
        assert rolled[month] == pytest.approx(value, abs=0.01 * 31)


def test_fill_gaps_covers_full_range(big, total):
    filled = revenue.revenue_by_period(
        big.orders, "day", fill_gaps=True, start=date(2024, 1, 1), end=date(2025, 12, 31)
    )
    assert len(filled) == 731
    assert sum(filled.values()) == pytest.approx(total, abs=0.01 * 731)


def test_gross_minus_discount_is_net(big, total):
    gross = revenue.gross_revenue(big.orders)
    discount = revenue.total_discount(big.orders)
    assert gross - discount == pytest.approx(total, abs=0.05)
    assert 0 < discount < gross * 0.2


def test_aov_times_count_is_total(big, total):
    count = len(revenue.revenue_orders(big.orders))
    # AOV is rounded to cents, so the product can drift by at most half a cent per order
    assert revenue.average_order_value(big.orders) * count == pytest.approx(total, abs=0.005 * count)


def test_regional_aov_weighted_mean_is_overall_aov(big):
    by_id = big.customer_index()
    counts: dict[str, int] = defaultdict(int)
    for o in revenue.revenue_orders(big.orders):
        counts[by_id[o.customerId].region.value] += 1
    aov = revenue.aov_by_region(big.orders, big.customers)
    weighted = sum(aov[r] * counts[r] for r in aov) / sum(counts.values())
    assert weighted == pytest.approx(revenue.average_order_value(big.orders), abs=0.01)


def test_coupon_discounts_match_coupon_rates(big):
    usage = revenue.coupon_usage(big.orders)
    assert set(usage) == set(COUPONS)
    for code, stats in usage.items():
        rate = stats["discount"] / (stats["revenue"] + stats["discount"])
        assert rate == pytest.approx(COUPONS[code], abs=0.002)
