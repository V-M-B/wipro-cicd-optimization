from __future__ import annotations

import pytest

from app.metrics import timeseries as ts


@pytest.mark.parametrize(
    ("values", "expected"),
    [([2, 4, 4, 4, 5, 5, 7, 9], (5.0, 2.0)), ([1], (1.0, 0.0)), ([3, 3], (3.0, 0.0)), ([-1, 1], (0.0, 1.0))],
)
def test_mean_std(values, expected):
    assert ts.mean_std(values) == pytest.approx(expected)


def test_mean_std_empty():
    with pytest.raises(ValueError, match="empty"):
        ts.mean_std([])


def test_zscores_constant_series():
    assert ts.zscores([4, 4, 4]) == [0.0, 0.0, 0.0]


@pytest.mark.parametrize(
    ("values", "threshold", "expected"),
    [
        ([10] * 9 + [100], 3.0, []),  # z is exactly 3.0: not strictly greater
        ([10] * 9 + [100], 2.5, [(9, 3.0, "high")]),
        ([50] * 9 + [-40], 2.9, [(9, -3.0, "low")]),
        ([1, 1, 1, 1], 1.0, []),
        ([], 3.0, []),
        ([1, 2, 3, 4, 5], 1.4, [(0, -1.414214, "low"), (4, 1.414214, "high")]),
    ],
)
def test_zscore_anomalies(values, threshold, expected):
    found = ts.zscore_anomalies(values, threshold)
    assert [(a.index, a.score, a.direction) for a in found] == expected


@pytest.mark.parametrize(
    ("values", "q", "expected"),
    [
        ([1, 2, 3, 4], 0.25, 1.75),
        ([1, 2, 3, 4], 0.5, 2.5),
        ([1, 2, 3, 4], 0.75, 3.25),
        ([1, 2, 3, 4], 0.0, 1.0),
        ([1, 2, 3, 4], 1.0, 4.0),
        ([5], 0.3, 5.0),
        ([4, 1, 3, 2], 0.5, 2.5),
        ([1, 2, 3, 4, 5], 0.5, 3.0),
    ],
)
def test_quantile(values, q, expected):
    assert ts.quantile(values, q) == pytest.approx(expected)


@pytest.mark.parametrize(("values", "q"), [([], 0.5), ([1, 2], -0.1), ([1, 2], 1.1)])
def test_quantile_validation(values, q):
    with pytest.raises(ValueError, match=r"values must not be empty|q must be"):
        ts.quantile(values, q)


@pytest.mark.parametrize(
    ("values", "k", "expected"),
    [
        ([1, 2, 3, 4, 100], 1.5, (-1.0, 7.0)),
        ([1, 2, 3, 4, 5, 6, 7, 8], 1.5, (-2.5, 11.5)),
        ([1, 2, 3, 4, 5], 0.0, (2.0, 4.0)),
        ([7, 7, 7], 3.0, (7.0, 7.0)),
    ],
)
def test_iqr_bounds(values, k, expected):
    assert ts.iqr_bounds(values, k) == pytest.approx(expected)


def test_iqr_bounds_reject_negative_k():
    with pytest.raises(ValueError, match="k must be"):
        ts.iqr_bounds([1, 2, 3], -1)


@pytest.mark.parametrize(
    ("values", "k", "expected"),
    [
        ([1, 2, 3, 4, 100], 1.5, [(4, 93.0, "high")]),
        ([1, 2, 3, 4, 5, 6, 7, 8], 1.5, []),
        ([1, 2, 3, 4, 5], 0.0, [(0, 1.0, "low"), (4, 1.0, "high")]),
        ([], 1.5, []),
        ([7, 7, 7, 8], 1.5, [(3, 0.375, "high")]),
    ],
)
def test_iqr_anomalies(values, k, expected):
    assert [(a.index, a.score, a.direction) for a in ts.iqr_anomalies(values, k)] == expected


@pytest.mark.parametrize(
    ("values", "window", "threshold", "expected"),
    [
        ([10, 10, 10, 10, 10, 50], 5, 3.0, [(5, None, "high")]),
        ([10, 10, 10, 10, 10, 10], 5, 3.0, []),
        ([1, 2, 1, 2, 1, 2, 10], 6, 3.0, [(6, 17.0, "high")]),
        ([1, 2, 1, 2, 1, 2, -10], 6, 3.0, [(6, -23.0, "low")]),
        ([1, 2, 1, 2, 1, 2, 2.5], 6, 3.0, []),
        ([1, 2, 3], 5, 3.0, []),
    ],
)
def test_rolling_zscore_anomalies(values, window, threshold, expected):
    found = ts.rolling_zscore_anomalies(values, window, threshold)
    assert [(a.index, a.score, a.direction) for a in found] == expected


@pytest.mark.parametrize(("window", "threshold"), [(0, 3.0), (3, 0.0), (3, -1.0)])
def test_rolling_validation(window, threshold):
    with pytest.raises(ValueError, match=r"window|threshold"):
        ts.rolling_zscore_anomalies([1, 2, 3, 4], window, threshold)


def test_anomaly_as_dict():
    (anomaly,) = ts.iqr_anomalies([1, 2, 3, 4, 100])
    assert anomaly.as_dict() == {"index": 4, "value": 100.0, "score": 93.0, "direction": "high"}


def test_injected_spike_is_detected_in_generated_revenue(medium_dataset):
    series = list(ts.daily_revenue(medium_dataset.orders).values())
    spiked = list(series)
    spiked[200] = max(series) * 10
    z_idx = {a.index for a in ts.zscore_anomalies(spiked, 3.0)}
    iqr_idx = {a.index for a in ts.iqr_anomalies(spiked, 3.0)}
    assert 200 in z_idx
    assert 200 in iqr_idx
