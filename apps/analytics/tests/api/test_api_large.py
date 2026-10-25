"""End-to-end API calls with 20k-order payloads (JSON validation + metrics)."""

from __future__ import annotations

from datetime import date

import pytest

from app.metrics import customers, funnel, revenue
from tests.factories import dump, large_dataset

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def big():
    return large_dataset(20_000, seed=707)


@pytest.fixture(scope="module")
def payload(big):
    return {"orders": dump(big.orders), "customers": dump(big.customers), "products": dump(big.products)}


def test_revenue_summary_matches_library(client, big, payload):
    body = client.post("/revenue/summary", json=payload).json()
    expected = revenue.revenue_summary(big.orders, big.customers, big.products)
    assert body == expected


def test_rfm_matches_library(client, big, payload):
    body = client.post("/customers/rfm", json={"orders": payload["orders"], "as_of": "2025-12-31"}).json()
    expected = customers.segment_counts(customers.rfm_scores(big.orders, date(2025, 12, 31)))
    assert body["segments"] == expected


def test_funnel_by_region_matches_library(client, big, payload):
    body = client.post("/funnel", json={**payload, "by_region": True}).json()
    expected = funnel.funnel_by_region(big.orders, big.customers)
    assert body["by_region"] == {k: [s.as_dict() for s in v] for k, v in expected.items()}
