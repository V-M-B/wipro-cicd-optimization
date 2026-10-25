from __future__ import annotations

import pytest

from app.metrics import timeseries as ts


def _approx(values):
    return [None if v is None else pytest.approx(v, abs=1e-6) for v in values]


@pytest.mark.parametrize(
    ("values", "window", "expected"),
    [
        ([1, 2, 3, 4, 5], 2, [None, 1.5, 2.5, 3.5, 4.5]),
        ([1, 2, 3, 4, 5], 1, [1, 2, 3, 4, 5]),
        ([1, 2, 3, 4, 5], 5, [None, None, None, None, 3.0]),
        ([1, 2, 3], 6, [None, None, None]),
        ([], 3, []),
        ([10, 0, 10, 0], 2, [None, 5.0, 5.0, 5.0]),
        ([0.1, 0.2, 0.3], 3, [None, None, 0.2]),
    ],
)
def test_simple_moving_average(values, window, expected):
    assert ts.simple_moving_average(values, window) == _approx(expected)


@pytest.mark.parametrize(
    ("values", "window", "expected"),
    [
        ([1, 2, 3], 2, [None, 5 / 3, 8 / 3]),
        ([1, 2, 3], 1, [1, 2, 3]),
        ([3, 3, 3, 3], 3, [None, None, 3.0, 3.0]),
        ([0, 0, 6], 3, [None, None, 3.0]),
    ],
)
def test_weighted_moving_average(values, window, expected):
    assert ts.weighted_moving_average(values, window) == _approx(expected)


@pytest.mark.parametrize(
    ("values", "alpha", "expected"),
    [
        ([10, 20, 30], 0.5, [10, 15, 22.5]),
        ([10, 20, 30], 1.0, [10, 20, 30]),
        ([5, 5, 5], 0.3, [5, 5, 5]),
        ([0, 100], 0.25, [0, 25]),
        ([], 0.5, []),
    ],
)
def test_exponential_smoothing(values, alpha, expected):
    assert ts.exponential_smoothing(values, alpha) == _approx(expected)


def test_exponential_smoothing_stays_within_range():
    values = [3, 9, 1, 7, 4, 8, 2]
    smoothed = ts.exponential_smoothing(values, 0.4)
    assert all(min(values) <= s <= max(values) for s in smoothed)


def test_holt_recovers_linear_trend():
    fitted, forecast = ts.holt_linear([1, 2, 3, 4], 0.5, 0.5, horizon=3)
    assert fitted == _approx([1, 2, 3, 4])
    assert forecast == _approx([5, 6, 7])


@pytest.mark.parametrize(
    ("values", "horizon", "expected"),
    [([], 3, ([], [])), ([5], 2, ([5.0], [5.0, 5.0])), ([2, 2, 2], 0, ([2.0, 2.0, 2.0], []))],
)
def test_holt_edge_cases(values, horizon, expected):
    assert ts.holt_linear(values, 0.3, 0.2, horizon) == expected


def test_holt_forecast_follows_downward_trend():
    _, forecast = ts.holt_linear([100, 90, 80, 70, 60], 0.8, 0.8, horizon=2)
    assert forecast[0] < 60
    assert forecast[1] < forecast[0]


@pytest.mark.parametrize(
    ("func", "args", "message"),
    [
        (ts.simple_moving_average, ([1, 2], 0), "window"),
        (ts.weighted_moving_average, ([1, 2], -1), "window"),
        (ts.exponential_smoothing, ([1, 2], 0.0), "alpha"),
        (ts.exponential_smoothing, ([1, 2], 1.5), "alpha"),
        (ts.holt_linear, ([1, 2], 0.5, 0.0), "beta"),
        (ts.holt_linear, ([1, 2], 0.5, 0.5, -1), "horizon"),
    ],
)
def test_parameter_validation(func, args, message):
    with pytest.raises(ValueError, match=message):
        func(*args)


def test_sma_of_generated_daily_revenue_preserves_mean(medium_dataset):
    series = list(ts.daily_revenue(medium_dataset.orders).values())
    window = 7
    sma = [v for v in ts.simple_moving_average(series, window) if v is not None]
    assert len(sma) == len(series) - window + 1
    assert min(series) <= min(sma) <= max(sma) <= max(series)
