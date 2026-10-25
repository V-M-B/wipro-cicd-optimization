from __future__ import annotations

import pytest

from app.generated.schemas import Category
from app.io import csv_io

HEADER = "id,sku,name,category,unit_price,active\n"


def test_round_trip_tiny(tiny_products):
    assert csv_io.read_products(csv_io.write_products(tiny_products)) == tiny_products


def test_round_trip_generated_preserves_prices_exactly(small_dataset):
    restored = csv_io.read_products(csv_io.write_products(small_dataset.products))
    assert [p.unitPrice for p in restored] == [p.unitPrice for p in small_dataset.products]
    assert restored == small_dataset.products


def test_write_products_format(tiny_products):
    lines = csv_io.write_products(tiny_products[:1]).splitlines()
    assert lines == ["id,sku,name,category,unit_price,active", "P-ELE-1,ELE-1,Product ELE-1,ELECTRONICS,100.0,true"]


@pytest.mark.parametrize(("raw", "expected"), [("yes", True), ("0", False), ("TRUE", True)])
def test_active_flag_parsing(raw, expected):
    (product,) = csv_io.read_products(HEADER + f"P1,S1,Lamp,home,9.99,{raw}\n")
    assert product.active is expected
    assert product.category is Category.HOME


@pytest.mark.parametrize(
    ("row", "field"),
    [
        ("P1,S1,Lamp,HOME,-1,true", "unit_price"),
        ("P1,S1,Lamp,HOME,free,true", "unit_price"),
        ("P1,S1,Lamp,FOOD,1.0,true", "category"),
        ("P1,S1,Lamp,HOME,1.0,perhaps", "active"),
        ("P1,,Lamp,HOME,1.0,true", "sku"),
    ],
)
def test_invalid_product_rows(row, field):
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_products(HEADER + row + "\n")
    assert [e.field for e in excinfo.value.errors] == [field]


def test_duplicate_id_and_sku_are_reported_separately():
    text = HEADER + "P1,S1,Lamp,HOME,1,true\nP1,S2,Rug,HOME,1,true\nP3,S1,Mat,HOME,1,true\n"
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_products(text)
    assert [(e.line, e.field) for e in excinfo.value.errors] == [(3, "id"), (4, "sku")]
