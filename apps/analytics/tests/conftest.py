from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.datasets import Dataset, DatasetConfig, generate_dataset
from app.generated.schemas import Customer, Order, Product
from tests import factories

SMALL_CONFIG = DatasetConfig(seed=42, n_customers=120, n_products=40, n_orders=600)
MEDIUM_CONFIG = DatasetConfig(seed=2024, n_customers=400, n_products=80, n_orders=4_000)


@pytest.fixture
def tiny_orders() -> list[Order]:
    return factories.tiny_orders()


@pytest.fixture
def tiny_customers() -> list[Customer]:
    return factories.tiny_customers()


@pytest.fixture
def tiny_products() -> list[Product]:
    return factories.tiny_products()


@pytest.fixture(scope="session")
def small_dataset() -> Dataset:
    return generate_dataset(SMALL_CONFIG)


@pytest.fixture(scope="session")
def medium_dataset() -> Dataset:
    return generate_dataset(MEDIUM_CONFIG)


@pytest.fixture(scope="session")
def as_of() -> date:
    """Fixed analysis date (never the wall clock)."""
    return date(2025, 12, 31)


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def tiny_payload(tiny_orders, tiny_customers, tiny_products) -> dict:
    return {
        "orders": factories.dump(tiny_orders),
        "customers": factories.dump(tiny_customers),
        "products": factories.dump(tiny_products),
    }
