from __future__ import annotations

import pytest

from app import __version__


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "analytics", "version": __version__}


def test_openapi_lists_routers(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/revenue/summary", "/products/top", "/customers/rfm", "/timeseries/smooth", "/funnel", "/demo"):
        assert path in paths


def test_demo_defaults(client):
    body = client.get("/demo").json()
    assert body["config"] == {
        "seed": 42,
        "n_orders": 500,
        "n_customers": 100,
        "n_products": 40,
        "start": "2025-01-01",
        "end": "2025-12-31",
    }
    assert body["revenue"]["total_revenue"] > 0
    assert len(body["top_products"]) == 5
    assert [s["stage"] for s in body["funnel"]] == ["CREATED", "PAID", "SHIPPED", "DELIVERED"]
    assert sum(body["segments"].values()) > 0


def test_demo_is_deterministic(client):
    params = {"seed": 9, "n_orders": 300}
    assert client.get("/demo", params=params).json() == client.get("/demo", params=params).json()


def test_demo_seed_changes_output(client):
    a = client.get("/demo", params={"seed": 1}).json()["revenue"]["total_revenue"]
    b = client.get("/demo", params={"seed": 2}).json()["revenue"]["total_revenue"]
    assert a != b


@pytest.mark.parametrize(
    "params",
    [{"n_orders": 20001}, {"n_orders": -1}, {"n_customers": 0}, {"n_products": 1}, {"start": "not-a-date"}],
)
def test_demo_rejects_invalid_query(client, params):
    assert client.get("/demo", params=params).status_code == 422


def test_demo_rejects_reversed_dates(client):
    response = client.get("/demo", params={"start": "2025-06-01", "end": "2025-01-01"})
    assert response.status_code == 422
    assert "end must not be before start" in response.json()["detail"]


def test_unknown_route_is_404(client):
    assert client.get("/nope").status_code == 404
