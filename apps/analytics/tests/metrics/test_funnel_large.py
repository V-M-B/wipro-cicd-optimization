"""Data-heavy funnel invariants over a 40k-order generated dataset."""

from __future__ import annotations

import pytest

from app.metrics import funnel
from app.metrics.common import order_day, period_key
from tests.factories import large_dataset

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def big():
    return large_dataset(40_000, seed=505)


def test_funnel_reach_is_monotone(big):
    reached = [s.reached for s in funnel.funnel(big.orders)]
    assert reached[0] == len(big.orders)
    assert reached == sorted(reached, reverse=True)


def test_regional_funnels_sum_to_overall(big):
    overall = [s.reached for s in funnel.funnel(big.orders)]
    by_region = funnel.funnel_by_region(big.orders, big.customers)
    summed = [sum(stages[i].reached for stages in by_region.values()) for i in range(4)]
    assert summed == overall


def test_monthly_cancellation_rates_average_to_overall(big):
    monthly = funnel.cancellation_by_period(big.orders, "month")
    counts: dict[str, int] = {}
    for o in big.orders:
        key = period_key(order_day(o), "month")
        counts[key] = counts.get(key, 0) + 1
    weighted = sum(monthly[k] * counts[k] for k in monthly) / len(big.orders)
    assert weighted == pytest.approx(funnel.cancellation_rate(big.orders), abs=1e-3)
