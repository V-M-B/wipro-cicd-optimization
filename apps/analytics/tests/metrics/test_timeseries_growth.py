from __future__ import annotations

from datetime import date

import pytest

from app.metrics import timeseries as ts
from app.metrics.revenue import revenue_by_period, total_revenue


@pytest.mark.parametrize(
    ("values", "lag", "expected"),
    [
        ([100, 110, 99, 0, 50], 1, [None, 0.1, -0.1, -1.0, None]),
        ([1, 2, 3, 4], 2, [None, None, 2.0, 1.0]),
        ([-10, -5], 1, [None, 0.5]),
        ([5], 1, [None]),
        ([], 1, []),
    ],
)
def test_pct_change(values, lag, expected):
    result = ts.pct_change(values, lag)
    assert result == [None if e is None else pytest.approx(e) for e in expected]


def test_pct_change_rejects_bad_lag():
    with pytest.raises(ValueError, match="lag"):
        ts.pct_change([1, 2], 0)


def test_daily_series_fills_missing_days():
    data = {date(2025, 1, 1): 5.0, date(2025, 1, 3): 2.0}
    assert ts.daily_series(data, date(2025, 1, 1), date(2025, 1, 4)) == [5.0, 0.0, 2.0, 0.0]


def test_daily_series_rejects_reversed_range():
    with pytest.raises(ValueError, match="end must not be before start"):
        ts.daily_series({}, date(2025, 1, 2), date(2025, 1, 1))


def test_daily_revenue(tiny_orders):
    assert ts.daily_revenue(tiny_orders) == {
        date(2025, 1, 6): 120.0,
        date(2025, 1, 7): 20.0,
        date(2025, 1, 15): 90.0,
        date(2025, 2, 3): 70.0,
        date(2025, 3, 1): 120.0,
        date(2025, 3, 2): 30.0,
    }


DAILY = {date(2025, 1, 6): 10.0, date(2025, 1, 8): 5.0, date(2025, 1, 13): 30.0, date(2025, 1, 27): 20.0}


def test_weekly_totals():
    assert ts.weekly_totals(DAILY) == {"2025-W02": 15.0, "2025-W03": 30.0, "2025-W05": 20.0}


def test_week_over_week():
    assert ts.week_over_week(DAILY) == [
        {"week": "2025-W02", "total": 15.0, "growth": None},
        {"week": "2025-W03", "total": 30.0, "growth": 1.0},
        {"week": "2025-W04", "total": 0.0, "growth": -1.0},
        {"week": "2025-W05", "total": 20.0, "growth": None},
    ]


def test_week_over_week_empty():
    assert ts.week_over_week({}) == []


def test_week_over_week_across_iso_year_boundary():
    data = {date(2024, 12, 30): 10.0, date(2025, 1, 6): 12.0}
    assert ts.week_over_week(data) == [
        {"week": "2025-W01", "total": 10.0, "growth": None},
        {"week": "2025-W02", "total": 12.0, "growth": 0.2},
    ]


def test_weekly_totals_match_revenue_by_week(medium_dataset):
    weekly = ts.weekly_totals(ts.daily_revenue(medium_dataset.orders))
    by_week = revenue_by_period(medium_dataset.orders, "week")
    assert list(weekly) == list(by_week)
    assert [round(v, 2) for v in weekly.values()] == pytest.approx(list(by_week.values()), abs=0.01)


def test_week_over_week_rows_are_contiguous(medium_dataset):
    rows = ts.week_over_week(ts.daily_revenue(medium_dataset.orders))
    assert len(rows) in (52, 53)
    assert sum(r["total"] for r in rows) == pytest.approx(total_revenue(medium_dataset.orders), abs=0.5)
