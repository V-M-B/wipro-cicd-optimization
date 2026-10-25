from __future__ import annotations

import pytest


def test_summary(client, tiny_payload):
    body = client.post("/revenue/summary", json=tiny_payload).json()
    assert body["total_revenue"] == 450.0
    assert body["order_count"] == 6
    assert body["by_region"]["NORTH"] == 330.0
    assert body["by_category"]["ELECTRONICS"] == 260.0
    assert body["by_period"] == {"2025-01": 230.0, "2025-02": 70.0, "2025-03": 150.0}


@pytest.mark.parametrize(
    ("granularity", "fill_gaps", "expected_len"),
    [("day", False, 6), ("week", False, 4), ("week", True, 8), ("month", True, 3), ("day", True, 56)],
)
def test_by_period(client, tiny_payload, granularity, fill_gaps, expected_len):
    body = client.post("/revenue/by-period", json={**tiny_payload, "granularity": granularity, "fill_gaps": fill_gaps})
    assert body.status_code == 200
    assert len(body.json()) == expected_len
    assert sum(body.json().values()) == pytest.approx(450.0)


def test_by_period_rejects_unknown_granularity(client, tiny_payload):
    response = client.post("/revenue/by-period", json={**tiny_payload, "granularity": "quarter"})
    assert response.status_code == 422


def test_by_region_and_category(client, tiny_payload):
    assert client.post("/revenue/by-region", json=tiny_payload).json()["UNKNOWN"] == 30.0
    assert client.post("/revenue/by-category", json=tiny_payload).json()["GROCERY"] == 70.0


def test_aov(client, tiny_payload):
    body = client.post("/revenue/aov", json=tiny_payload).json()
    assert body["average_order_value"] == 75.0
    assert body["by_region"]["NORTH"] == 110.0


def test_coupons(client, tiny_payload):
    body = client.post("/revenue/coupons", json={"orders": tiny_payload["orders"]}).json()
    assert body == {"SAVE10": {"orders": 1, "revenue": 90.0, "discount": 10.0}}


def test_invalid_order_payload_is_rejected(client, tiny_payload):
    broken = dict(tiny_payload["orders"][0], status="LOST")
    response = client.post("/revenue/summary", json={"orders": [broken]})
    assert response.status_code == 422


def test_missing_orders_field(client):
    assert client.post("/revenue/summary", json={}).status_code == 422
