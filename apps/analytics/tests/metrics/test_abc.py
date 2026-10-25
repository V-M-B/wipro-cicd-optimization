from __future__ import annotations

import pytest

from app.metrics import products


@pytest.mark.parametrize(
    ("values", "thresholds", "expected"),
    [
        ({"a": 80, "b": 15, "c": 5}, (0.8, 0.95), {"a": "A", "b": "B", "c": "C"}),
        ({"x": 100}, (0.8, 0.95), {"x": "A"}),
        ({"a": 50, "b": 30, "c": 10, "d": 10}, (0.8, 0.95), {"a": "A", "b": "A", "c": "B", "d": "B"}),
        ({"a": 1, "b": 1, "c": 1, "d": 1}, (0.8, 0.95), {"a": "A", "b": "A", "c": "A", "d": "A"}),
        ({"a": 0, "b": 0}, (0.8, 0.95), {"a": "C", "b": "C"}),
        ({"a": 10, "b": -5}, (0.8, 0.95), {"a": "A", "b": "C"}),
        ({"a": 40, "b": 30, "c": 20, "d": 10}, (0.5, 0.9), {"a": "A", "b": "A", "c": "B", "d": "C"}),
        ({"a": 90, "b": 6, "c": 4}, (0.8, 0.95), {"a": "A", "b": "B", "c": "C"}),
        ({"a": 70, "b": 20, "c": 6, "d": 4}, (0.8, 0.95), {"a": "A", "b": "A", "c": "B", "d": "C"}),
        ({}, (0.8, 0.95), {}),
    ],
)
def test_abc_classification(values, thresholds, expected):
    assert products.abc_classification(values, *thresholds) == expected


@pytest.mark.parametrize(("a", "b"), [(0.0, 0.5), (0.5, 0.5), (0.9, 0.8), (0.5, 1.1), (-0.1, 0.5)])
def test_abc_rejects_bad_thresholds(a, b):
    with pytest.raises(ValueError, match="thresholds"):
        products.abc_classification({"a": 1.0}, a, b)


def test_abc_first_item_is_always_a_even_if_dominant():
    assert products.abc_classification({"big": 99.0, "small": 1.0})["big"] == "A"


def test_abc_ties_are_ordered_by_key():
    classes = products.abc_classification({"b": 50.0, "a": 50.0}, 0.5, 0.9)
    assert classes == {"a": "A", "b": "B"}


def test_abc_for_products_includes_unsold(tiny_orders, tiny_products):
    classes = products.abc_for_products(tiny_orders, tiny_products)
    assert classes == {"ELE-1": "A", "APP-1": "A", "GRO-1": "A", "ELE-2": "B", "ZZZ-9": "B", "TOY-1": "C"}


def test_abc_for_products_excluding_unsold(tiny_orders, tiny_products):
    classes = products.abc_for_products(tiny_orders, tiny_products, include_unsold=False)
    assert "TOY-1" not in classes


def test_abc_summary(tiny_orders, tiny_products):
    classes = products.abc_for_products(tiny_orders, tiny_products)
    values = {sku: s.revenue for sku, s in products.product_sales(tiny_orders, tiny_products).items()}
    assert products.abc_summary(classes, values) == {
        "A": {"count": 3, "share": 0.8},
        "B": {"count": 2, "share": 0.2},
        "C": {"count": 1, "share": 0.0},
    }


def test_abc_summary_empty():
    assert products.abc_summary({}, {}) == {
        "A": {"count": 0, "share": 0.0},
        "B": {"count": 0, "share": 0.0},
        "C": {"count": 0, "share": 0.0},
    }


def test_abc_class_a_holds_about_80_percent_on_generated_data(medium_dataset):
    ds = medium_dataset
    classes = products.abc_for_products(ds.orders, ds.products)
    values = {sku: s.revenue for sku, s in products.product_sales(ds.orders, ds.products).items()}
    summary = products.abc_summary(classes, values)
    assert 0.8 <= summary["A"]["share"] < 0.8 + max(values.values()) / sum(values.values()) + 1e-9
    assert summary["B"]["count"] > 0
    assert summary["C"]["count"] > summary["A"]["count"]


def test_abc_classes_are_monotone_in_value(medium_dataset):
    ds = medium_dataset
    sales = products.product_sales(ds.orders, ds.products)
    classes = products.abc_for_products(ds.orders, ds.products)
    rank = {"A": 0, "B": 1, "C": 2}
    ordered = sorted(sales.values(), key=lambda s: (-s.revenue, s.sku))
    assert [rank[classes[s.sku]] for s in ordered] == sorted(rank[classes[s.sku]] for s in ordered)
