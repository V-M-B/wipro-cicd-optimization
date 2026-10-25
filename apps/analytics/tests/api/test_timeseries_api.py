from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"values": [1, 2, 3, 4], "method": "sma", "window": 2}, [None, 1.5, 2.5, 3.5]),
        ({"values": [10, 20, 30], "method": "ema", "alpha": 0.5}, [10.0, 15.0, 22.5]),
        ({"values": [3, 3, 3], "method": "wma", "window": 3}, [None, None, 3.0]),
    ],
)
def test_smooth(client, payload, expected):
    assert client.post("/timeseries/smooth", json=payload).json() == {"values": expected}


def test_smooth_holt_forecast(client):
    payload = {"values": [1, 2, 3, 4], "method": "holt", "alpha": 0.5, "beta": 0.5, "horizon": 2}
    body = client.post("/timeseries/smooth", json=payload).json()
    assert body["forecast"] == pytest.approx([5.0, 6.0])


def test_smooth_invalid_window(client):
    response = client.post("/timeseries/smooth", json={"values": [1, 2], "window": 0})
    assert response.status_code == 422
    assert response.json() == {"detail": "window must be >= 1"}


@pytest.mark.parametrize(
    ("payload", "indices"),
    [
        ({"values": [10] * 9 + [100], "method": "zscore", "threshold": 2.5}, [9]),
        ({"values": [1, 2, 3, 4, 100], "method": "iqr"}, [4]),
        ({"values": [10, 10, 10, 10, 10, 50], "method": "rolling", "window": 5}, [5]),
    ],
)
def test_anomalies(client, payload, indices):
    body = client.post("/timeseries/anomalies", json=payload).json()
    assert [a["index"] for a in body["anomalies"]] == indices
    assert body["count"] == len(indices)


def test_week_over_week(client, tiny_payload):
    rows = client.post("/timeseries/week-over-week", json={"orders": tiny_payload["orders"]}).json()
    assert rows[0] == {"week": "2025-W02", "total": 140.0, "growth": None}
    assert rows[1] == {"week": "2025-W03", "total": 90.0, "growth": -0.3571}
    assert len(rows) == 8
