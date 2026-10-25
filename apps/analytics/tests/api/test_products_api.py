from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("by", "first"),
    [("revenue", "ELE-1"), ("units", "GRO-1"), ("orders", "ELE-2")],
)
def test_top(client, tiny_payload, by, first):
    body = client.post("/products/top", json={**tiny_payload, "n": 3, "by": by}).json()
    assert len(body) == 3
    assert body[0]["sku"] == first


def test_top_rejects_negative_n(client, tiny_payload):
    assert client.post("/products/top", json={**tiny_payload, "n": -1}).status_code == 422


def test_abc(client, tiny_payload):
    body = client.post("/products/abc", json=tiny_payload).json()
    assert body["classes"]["TOY-1"] == "C"
    assert body["summary"]["A"] == {"count": 3, "share": 0.8}


def test_abc_invalid_thresholds_map_to_422(client, tiny_payload):
    response = client.post("/products/abc", json={**tiny_payload, "a": 0.9, "b": 0.5})
    assert response.status_code == 422
    assert "thresholds" in response.json()["detail"]


def test_affinity(client, tiny_payload):
    body = client.post("/products/affinity", json={"orders": tiny_payload["orders"], "limit": 2}).json()
    assert [(r["antecedent"], r["consequent"]) for r in body] == [("GRO-1", "ELE-1"), ("GRO-1", "ELE-2")]
    assert body[0]["lift"] == 1.333333
