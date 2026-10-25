from __future__ import annotations

from datetime import datetime

import pytest

from app.generated.schemas import OrderStatus
from app.io import csv_io
from app.metrics.revenue import total_revenue
from tests.factories import make_order

HEADER = "order_id,customer_id,status,created_at,coupon_code,total,sku,quantity,unit_price\n"


def test_round_trip_tiny(tiny_orders):
    assert csv_io.read_orders(csv_io.write_orders(tiny_orders)) == tiny_orders


def test_round_trip_generated(small_dataset):
    text = csv_io.write_orders(small_dataset.orders)
    restored = csv_io.read_orders(text)
    assert restored == small_dataset.orders
    assert total_revenue(restored) == total_revenue(small_dataset.orders)


def test_one_row_per_line(tiny_orders):
    rows = csv_io.write_orders(tiny_orders).splitlines()
    assert len(rows) == 1 + sum(len(o.lines) for o in tiny_orders)


def test_order_without_lines_round_trips():
    order = make_order("O1", lines=[], total=5.0)
    text = csv_io.write_orders([order])
    assert text.splitlines()[1] == "O1,C1,DELIVERED,2025-01-01T12:00:00,,5.0,,,"
    assert csv_io.read_orders(text) == [order]


def test_rows_of_an_order_need_not_be_adjacent():
    text = (
        HEADER
        + "O1,C1,PAID,2025-01-01T00:00:00,,30,A,1,10\n"
        + "O2,C2,PAID,2025-01-02T00:00:00,,5,B,1,5\n"
        + "O1,C1,PAID,2025-01-01T00:00:00,,30,C,2,10\n"
    )
    orders = csv_io.read_orders(text)
    assert [o.id for o in orders] == ["O1", "O2"]
    assert [line.sku for line in orders[0].lines] == ["A", "C"]


def test_coupon_and_timezone_are_parsed():
    (order,) = csv_io.read_orders(HEADER + "O1,C1,shipped,2025-06-01T08:00:00Z,SAVE10,9,A,1,10\n")
    assert order.status is OrderStatus.SHIPPED
    assert order.couponCode == "SAVE10"
    assert order.createdAt.utcoffset().total_seconds() == 0
    assert order.createdAt.replace(tzinfo=None) == datetime(2025, 6, 1, 8)


@pytest.mark.parametrize(
    ("row", "field"),
    [
        ("O1,C1,LOST,2025-01-01,,10,A,1,10", "status"),
        ("O1,C1,PAID,someday,,10,A,1,10", "created_at"),
        ("O1,C1,PAID,2025-01-01,,-10,A,1,10", "total"),
        ("O1,C1,PAID,2025-01-01,,10,A,0,10", "quantity"),
        ("O1,C1,PAID,2025-01-01,,10,A,two,10", "quantity"),
        ("O1,C1,PAID,2025-01-01,,10,A,1,-10", "unit_price"),
        ("O1,C1,PAID,2025-01-01,,10,,1,10", "sku"),
        ("O1,,PAID,2025-01-01,,10,A,1,10", "customer_id"),
        (",C1,PAID,2025-01-01,,10,A,1,10", "order_id"),
    ],
)
def test_invalid_order_rows(row, field):
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_orders(HEADER + row + "\n")
    assert [(e.line, e.field) for e in excinfo.value.errors] == [(2, field)]


def test_inconsistent_order_header_fields():
    text = HEADER + "O1,C1,PAID,2025-01-01,,10,A,1,5\nO1,C2,PAID,2025-01-01,,12,B,1,5\n"
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_orders(text)
    assert [(e.line, e.field) for e in excinfo.value.errors] == [(3, "customer_id"), (3, "total")]
    assert "inconsistent with line 2" in excinfo.value.errors[0].message


def test_duplicate_sku_within_order():
    text = HEADER + "O1,C1,PAID,2025-01-01,,10,A,1,5\nO1,C1,PAID,2025-01-01,,10,A,1,5\n"
    with pytest.raises(csv_io.CsvValidationError, match="duplicate sku 'A' in order 'O1'"):
        csv_io.read_orders(text)


def test_missing_order_columns():
    with pytest.raises(csv_io.CsvValidationError, match="missing required column"):
        csv_io.read_orders("order_id,customer_id\nO1,C1\n")
