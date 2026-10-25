"""Data-heavy customer invariants over an 80k-order generated dataset."""

from __future__ import annotations

import itertools
from datetime import date

import pytest

from app.metrics import customers
from app.metrics.common import ACTIVE_STATUSES, REVENUE_STATUSES
from tests.factories import large_dataset

pytestmark = pytest.mark.slow

AS_OF = date(2025, 12, 31)


@pytest.fixture(scope="module")
def big():
    return large_dataset(80_000, seed=303)


@pytest.fixture(scope="module")
def rfm(big):
    return customers.rfm_scores(big.orders, AS_OF)


@pytest.fixture(scope="module")
def active(big):
    return customers.cohort_retention(big.orders, "active")


@pytest.fixture(scope="module")
def rolling(big):
    return customers.cohort_retention(big.orders, "rolling")


def test_rfm_covers_every_paying_customer(big, rfm):
    paying = {o.customerId for o in big.orders if o.status in REVENUE_STATUSES}
    assert {r.customer_id for r in rfm} == paying
    assert sum(customers.segment_counts(rfm).values()) == len(paying)


def test_monetary_quintiles_are_balanced(rfm):
    for score in range(1, 6):
        share = sum(1 for r in rfm if r.m == score) / len(rfm)
        assert 0.15 <= share <= 0.25


def test_rfm_frequency_matches_order_counts(big, rfm):
    counts: dict[str, int] = {}
    for o in big.orders:
        if o.status in REVENUE_STATUSES:
            counts[o.customerId] = counts.get(o.customerId, 0) + 1
    assert all(counts[r.customer_id] == r.frequency for r in rfm)


def test_active_retention_matrix_is_well_formed(active):
    assert len(active.cohorts) == 24
    assert [len(row) for row in active.rows] == list(range(24, 0, -1))
    for row in active.rows:
        assert row[0] == 1.0
        assert all(0.0 <= v <= 1.0 for v in row)


def test_rolling_retention_is_non_increasing(rolling):
    for row in rolling.rows:
        assert all(later <= earlier for earlier, later in itertools.pairwise(row))


def test_rolling_retention_dominates_active(active, rolling):
    for a_row, r_row in zip(active.rows, rolling.rows, strict=True):
        assert all(r >= a for a, r in zip(a_row, r_row, strict=True))


def test_cohort_sizes_partition_active_customers(big, active):
    active_customers = {o.customerId for o in big.orders if o.status in ACTIVE_STATUSES}
    assert sum(active.sizes) == len(active_customers)


def test_average_retention_curve_bounds(active):
    curve = customers.average_retention_curve(active)
    assert curve[0] == 1.0
    assert all(0.0 <= v <= 1.0 for v in curve)
    assert curve[1] > curve[-1]


def test_churn_rate_monotone_in_threshold(big):
    rates = [customers.churn_rate(customers.churn_flags(big.orders, AS_OF, t)) for t in (14, 30, 60, 120, 240, 480)]
    assert rates == sorted(rates, reverse=True)


def test_clv_scales_linearly_with_margin(big):
    low = customers.customer_clv(big.orders, AS_OF, gross_margin=0.2, retention=0.6)
    high = customers.customer_clv(big.orders, AS_OF, gross_margin=0.4, retention=0.6)
    assert set(low) == set(high)
    for cid, value in low.items():
        assert high[cid] == pytest.approx(2 * value, abs=0.02)
