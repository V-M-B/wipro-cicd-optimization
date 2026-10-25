"""Data-heavy time-series checks over a 50k-order generated dataset (731 daily points)."""

from __future__ import annotations

import statistics
from datetime import date

import pytest

from app.metrics import timeseries as ts
from app.metrics.revenue import total_revenue
from tests.factories import large_dataset

pytestmark = pytest.mark.slow

SPIKES = (100, 250, 400, 555, 700)


@pytest.fixture(scope="module")
def big():
    return large_dataset(50_000, seed=404)


@pytest.fixture(scope="module")
def series(big):
    return ts.daily_series(ts.daily_revenue(big.orders), date(2024, 1, 1), date(2025, 12, 31))


@pytest.fixture(scope="module")
def spiked(series):
    values = list(series)
    peak = max(series)
    for i in SPIKES:
        values[i] = peak * 6
    return values


@pytest.mark.parametrize("window", [3, 7, 28])
def test_sma_matches_brute_force(series, window):
    sma = ts.simple_moving_average(series, window)
    for i in range(window - 1, len(series)):
        assert sma[i] == pytest.approx(statistics.fmean(series[i - window + 1 : i + 1]), rel=1e-9, abs=1e-6)


def test_injected_spikes_found_by_zscore_and_iqr(spiked):
    z_found = {a.index for a in ts.zscore_anomalies(spiked, 3.0)}
    iqr_found = {a.index for a in ts.iqr_anomalies(spiked, 3.0)}
    assert set(SPIKES) <= z_found
    assert set(SPIKES) <= iqr_found


def test_injected_spikes_found_by_rolling_zscore(spiked):
    found = {a.index for a in ts.rolling_zscore_anomalies(spiked, window=28, threshold=4.0)}
    assert set(SPIKES) <= found


def test_quantiles_match_statistics_module(series):
    q1, _q2, q3 = statistics.quantiles(series, n=4, method="inclusive")
    assert ts.quantile(series, 0.25) == pytest.approx(q1)
    assert ts.quantile(series, 0.75) == pytest.approx(q3)


def test_weekly_rollup_reconciles(big, series):
    rows = ts.week_over_week(ts.daily_revenue(big.orders))
    assert sum(r["total"] for r in rows) == pytest.approx(total_revenue(big.orders), abs=0.01 * len(rows))
    assert sum(series) == pytest.approx(total_revenue(big.orders), abs=0.05)
