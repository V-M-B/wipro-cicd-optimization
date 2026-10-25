from __future__ import annotations

import pytest


def test_rfm(client, tiny_payload):
    body = client.post("/customers/rfm", json={"orders": tiny_payload["orders"], "as_of": "2025-03-31"}).json()
    codes = {c["customer_id"]: c["code"] for c in body["customers"]}
    assert codes == {"C1": "344", "C2": "111", "C3": "213", "C9": "412"}
    assert body["segments"]["Loyal"] == 1


def test_rfm_requires_as_of(client, tiny_payload):
    assert client.post("/customers/rfm", json={"orders": tiny_payload["orders"]}).status_code == 422


@pytest.mark.parametrize("mode", ["active", "rolling"])
def test_retention(client, tiny_payload, mode):
    body = client.post("/customers/retention", json={"orders": tiny_payload["orders"], "mode": mode}).json()
    assert body["mode"] == mode
    assert body["cohorts"] == ["2025-01", "2025-02", "2025-03"]
    assert body["average"][0] == 1.0


def test_churn(client, tiny_payload):
    payload = {"orders": tiny_payload["orders"], "as_of": "2025-03-31", "threshold_days": 30}
    body = client.post("/customers/churn", json=payload).json()
    assert body["churn_rate"] == 0.6
    assert body["flags"]["C1"] is False


def test_churn_rejects_negative_threshold(client, tiny_payload):
    payload = {"orders": tiny_payload["orders"], "as_of": "2025-03-31", "threshold_days": -5}
    assert client.post("/customers/churn", json=payload).status_code == 422


def test_clv(client, tiny_payload):
    payload = {"orders": tiny_payload["orders"], "as_of": "2025-03-31", "retention": 0.5, "discount_rate": 0.0}
    body = client.post("/customers/clv", json=payload).json()
    assert body["clv"] == {"C1": 33.0, "C2": 2.0, "C3": 10.5, "C9": 9.0}
    assert body["total"] == 54.5


def test_clv_invalid_retention_is_422(client, tiny_payload):
    payload = {"orders": tiny_payload["orders"], "as_of": "2025-03-31", "retention": 1.0}
    response = client.post("/customers/clv", json=payload)
    assert response.status_code == 422
    assert "retention" in response.json()["detail"]
