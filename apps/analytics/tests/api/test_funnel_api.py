from __future__ import annotations


def test_funnel(client, tiny_payload):
    body = client.post("/funnel", json={"orders": tiny_payload["orders"]}).json()
    assert [s["reached"] for s in body["stages"]] == [8, 6, 5, 4]
    assert body["cancellation_rate"] == 0.125
    assert body["bottleneck"] == "PAID"
    assert body["status_counts"]["DELIVERED"] == 4
    assert "by_region" not in body


def test_funnel_by_region(client, tiny_payload):
    body = client.post("/funnel", json={**tiny_payload, "by_region": True}).json()
    assert [s["reached"] for s in body["by_region"]["NORTH"]] == [3, 3, 3, 2]
    assert set(body["by_region"]) == {"EAST", "NORTH", "SOUTH", "UNKNOWN", "WEST"}


def test_funnel_empty(client):
    body = client.post("/funnel", json={"orders": []}).json()
    assert body["bottleneck"] is None
    assert body["cancellation_rate"] == 0.0
