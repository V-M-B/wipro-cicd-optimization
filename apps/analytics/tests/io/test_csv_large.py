"""Data-heavy CSV round trips and bulk validation over a 20k-order dataset."""

from __future__ import annotations

import pytest

from app.io import csv_io
from tests.factories import large_dataset

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def big():
    return large_dataset(20_000, seed=606)


@pytest.fixture(scope="module")
def orders_csv(big):
    return csv_io.write_orders(big.orders)


def test_orders_round_trip(big, orders_csv):
    assert csv_io.read_orders(orders_csv) == big.orders


def test_customers_and_products_round_trip(big):
    assert csv_io.read_customers(csv_io.write_customers(big.customers)) == big.customers
    assert csv_io.read_products(csv_io.write_products(big.products)) == big.products


def test_bulk_corruption_reports_every_bad_row(orders_csv):
    lines = orders_csv.splitlines()
    corrupted = set(range(1, len(lines), 997))
    for i in corrupted:
        fields = lines[i].split(",")
        fields[7] = "0"  # quantity must be >= 1
        lines[i] = ",".join(fields)
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_orders("\n".join(lines) + "\n", max_errors=10_000)
    errors = excinfo.value.errors
    assert {e.line for e in errors} == {i + 1 for i in corrupted}
    assert {e.field for e in errors} == {"quantity"}
