"""Data-heavy product invariants over a 60k-order generated dataset."""

from __future__ import annotations

import pytest

from app.metrics import products, revenue
from tests.factories import large_dataset

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def big():
    return large_dataset(60_000, seed=202, n_products=300)


@pytest.fixture(scope="module")
def sales(big):
    return products.product_sales(big.orders, big.products)


def test_product_revenue_and_units_reconcile(big, sales):
    assert sum(s.revenue for s in sales.values()) == pytest.approx(revenue.total_revenue(big.orders), abs=0.01 * 300)
    assert sum(s.units for s in sales.values()) == revenue.units_sold(big.orders)


def test_top_n_lists_are_prefixes(big):
    full = products.top_products(big.orders, big.products, n=300)
    for n in (1, 5, 10, 50, 150):
        assert products.top_products(big.orders, big.products, n=n) == full[:n]


def test_abc_partition(big, sales):
    classes = products.abc_for_products(big.orders, big.products)
    values = {sku: s.revenue for sku, s in sales.items()}
    summary = products.abc_summary(classes, values)
    assert sum(int(v["count"]) for v in summary.values()) == len(big.products)
    assert summary["A"]["share"] >= 0.8
    assert summary["A"]["share"] + summary["B"]["share"] >= 0.95
    assert summary["A"]["share"] + summary["B"]["share"] + summary["C"]["share"] == pytest.approx(1.0, abs=1e-3)


def test_affinity_rules_are_consistent_with_co_occurrence(big):
    pairs = products.co_occurrence(big.orders)
    rules = products.affinity_rules(big.orders, min_support=0.001)
    assert rules
    n = len(big.orders)
    for rule in rules:
        key = tuple(sorted((rule.antecedent, rule.consequent)))
        assert rule.count == pairs[key]
        assert rule.support == pytest.approx(rule.count / n, abs=1e-6)


def test_bundle_pairs_have_positive_lift(big):
    rules = {(r.antecedent, r.consequent): r for r in products.affinity_rules(big.orders, min_support=0.0005)}
    skus = [p.sku for p in big.products]
    checked = 0
    for i in range(0, len(skus) - 1, 2):
        rule = rules.get((skus[i], skus[i + 1]))
        if rule is not None:
            checked += 1
            assert rule.lift > 1.5
    assert checked >= 50


def test_popular_products_are_bought_with_their_bundle_partner(big):
    position = {p.sku: i for i, p in enumerate(big.products)}
    top = products.top_products(big.orders, big.products, n=10, by="orders")
    for s in top:
        (partner, _count), *_ = products.frequently_bought_with(big.orders, s.sku, n=1)
        assert position[partner] == position[s.sku] ^ 1
