from __future__ import annotations

import pytest

from app.metrics import products
from app.metrics.revenue import total_revenue
from tests.factories import make_order


def test_product_sales(tiny_orders, tiny_products):
    sales = products.product_sales(tiny_orders, tiny_products)
    assert {sku: (s.units, s.revenue, s.orders) for sku, s in sales.items()} == {
        "APP-1": (2, 90.0, 1),
        "ELE-1": (2, 200.0, 2),
        "ELE-2": (3, 60.0, 3),
        "GRO-1": (7, 70.0, 2),
        "ZZZ-9": (1, 30.0, 1),
    }


def test_product_sales_unknown_sku_metadata(tiny_orders, tiny_products):
    unknown = products.product_sales(tiny_orders, tiny_products)["ZZZ-9"]
    assert unknown.name == "ZZZ-9"
    assert unknown.category == "UNKNOWN"


def test_product_sales_known_metadata(tiny_orders, tiny_products):
    ele = products.product_sales(tiny_orders, tiny_products)["ELE-1"]
    assert ele.name == "Product ELE-1"
    assert ele.category == "ELECTRONICS"
    assert ele.as_dict()["sku"] == "ELE-1"


def test_product_sales_all_statuses(tiny_orders, tiny_products):
    sales = products.product_sales(tiny_orders, tiny_products, statuses=None)
    assert sales["ELE-1"].units == 3  # includes the cancelled order
    assert sales["APP-1"].orders == 2  # includes the created order


@pytest.mark.parametrize(
    ("by", "expected"),
    [
        ("revenue", ["ELE-1", "APP-1", "GRO-1", "ELE-2", "ZZZ-9"]),
        ("units", ["GRO-1", "ELE-2", "APP-1", "ELE-1", "ZZZ-9"]),
        ("orders", ["ELE-2", "ELE-1", "GRO-1", "APP-1", "ZZZ-9"]),
    ],
)
def test_top_products_ranking(tiny_orders, tiny_products, by, expected):
    assert [s.sku for s in products.top_products(tiny_orders, tiny_products, n=10, by=by)] == expected


@pytest.mark.parametrize(("n", "expected_len"), [(0, 0), (1, 1), (3, 3), (5, 5), (50, 5)])
def test_top_products_limit(tiny_orders, tiny_products, n, expected_len):
    assert len(products.top_products(tiny_orders, tiny_products, n=n)) == expected_len


@pytest.mark.parametrize(("kwargs", "message"), [({"n": -1}, "n must be"), ({"by": "margin"}, "by must be")])
def test_top_products_invalid(tiny_orders, kwargs, message):
    with pytest.raises(ValueError, match=message):
        products.top_products(tiny_orders, **kwargs)


def test_top_products_is_sorted_on_generated_data(medium_dataset):
    top = products.top_products(medium_dataset.orders, medium_dataset.products, n=20)
    revenues = [s.revenue for s in top]
    assert revenues == sorted(revenues, reverse=True)


def test_top_product_revenue_never_exceeds_total(medium_dataset):
    total = total_revenue(medium_dataset.orders)
    sales = products.product_sales(medium_dataset.orders, medium_dataset.products)
    assert sum(s.revenue for s in sales.values()) == pytest.approx(total, abs=0.01 * len(sales))


def test_popularity_is_skewed(medium_dataset):
    top = products.top_products(medium_dataset.orders, medium_dataset.products, n=80, by="units")
    top_decile = sum(s.units for s in top[:8])
    bottom_half = sum(s.units for s in top[40:])
    assert top_decile > bottom_half


def test_category_unit_mix(tiny_orders, tiny_products):
    assert products.category_unit_mix(tiny_orders, tiny_products) == {
        "APPAREL": 0.1333,
        "ELECTRONICS": 0.3333,
        "GROCERY": 0.4667,
        "UNKNOWN": 0.0667,
    }


def test_category_unit_mix_empty():
    assert products.category_unit_mix([], []) == {}


def test_frequently_bought_with(tiny_orders):
    assert products.frequently_bought_with(tiny_orders, "ELE-1") == [("ELE-2", 1), ("GRO-1", 1)]
    assert products.frequently_bought_with(tiny_orders, "GRO-1", n=1) == [("ELE-1", 1)]
    assert products.frequently_bought_with(tiny_orders, "ZZZ-9") == []


def test_frequently_bought_with_counts_orders():
    orders = [
        make_order("O1", lines=[("A", 1, 1.0), ("B", 1, 1.0)]),
        make_order("O2", lines=[("A", 1, 1.0), ("B", 2, 1.0), ("C", 1, 1.0)]),
        make_order("O3", lines=[("A", 3, 1.0), ("C", 1, 1.0)]),
        make_order("O4", lines=[("A", 1, 1.0), ("B", 1, 1.0)]),
    ]
    assert products.frequently_bought_with(orders, "A") == [("B", 3), ("C", 2)]


def test_frequently_bought_with_rejects_negative_n(tiny_orders):
    with pytest.raises(ValueError, match="n must be"):
        products.frequently_bought_with(tiny_orders, "ELE-1", n=-2)
