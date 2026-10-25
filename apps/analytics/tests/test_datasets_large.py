"""Data-heavy generator checks (50k-100k orders)."""

from __future__ import annotations

import hashlib
from collections import Counter

import pytest

from app.datasets import DatasetConfig, generate_dataset
from app.generated.schemas import OrderStatus
from tests.factories import large_dataset

pytestmark = pytest.mark.slow


def _fingerprint(orders) -> str:
    digest = hashlib.sha256()
    for o in orders:
        digest.update(o.model_dump_json().encode())
    return digest.hexdigest()


def test_large_generation_is_deterministic():
    config = DatasetConfig(seed=808, n_orders=50_000, n_customers=2_500, n_products=200)
    assert _fingerprint(generate_dataset(config).orders) == _fingerprint(generate_dataset(config).orders)


def test_large_dataset_referential_integrity():
    ds = large_dataset(100_000, seed=809)
    customer_ids = {c.id for c in ds.customers}
    skus = {p.sku for p in ds.products}
    assert len(ds.orders) == 100_000
    assert all(o.customerId in customer_ids for o in ds.orders)
    assert all(line.sku in skus for o in ds.orders for line in o.lines)
    statuses = Counter(o.status for o in ds.orders)
    assert statuses[OrderStatus.DELIVERED] / len(ds.orders) > 0.8
