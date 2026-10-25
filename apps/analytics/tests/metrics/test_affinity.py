from __future__ import annotations

import pytest

from app.metrics import products
from app.metrics.common import REVENUE_STATUSES
from tests.factories import make_order


def test_co_occurrence(tiny_orders):
    assert products.co_occurrence(tiny_orders) == {
        ("ELE-1", "ELE-2"): 1,
        ("ELE-1", "GRO-1"): 1,
        ("ELE-2", "GRO-1"): 1,
    }


def test_co_occurrence_revenue_statuses_only(tiny_orders):
    assert products.co_occurrence(tiny_orders, REVENUE_STATUSES) == products.co_occurrence(tiny_orders)


def test_co_occurrence_counts_each_pair_once_per_order():
    orders = [make_order("O1", lines=[("A", 1, 1.0), ("B", 1, 1.0), ("C", 1, 1.0)])]
    assert products.co_occurrence(orders) == {("A", "B"): 1, ("A", "C"): 1, ("B", "C"): 1}


def test_co_occurrence_ignores_single_item_baskets():
    orders = [make_order("O1", lines=[("A", 4, 1.0)]), make_order("O2", lines=[("B", 1, 1.0)])]
    assert products.co_occurrence(orders) == {}


def test_affinity_rules_order_and_values(tiny_orders):
    rules = products.affinity_rules(tiny_orders)
    assert [(r.antecedent, r.consequent) for r in rules] == [
        ("GRO-1", "ELE-1"),
        ("GRO-1", "ELE-2"),
        ("ELE-1", "GRO-1"),
        ("ELE-2", "GRO-1"),
        ("ELE-1", "ELE-2"),
        ("ELE-2", "ELE-1"),
    ]
    first = rules[0]
    assert (first.count, first.support, first.confidence, first.lift) == (1, 0.125, 0.5, 1.333333)
    assert rules[-1].lift == 0.888889


@pytest.mark.parametrize(
    ("min_support", "min_confidence", "expected_count"),
    [(0.0, 0.0, 6), (0.125, 0.0, 6), (0.13, 0.0, 0), (0.0, 0.4, 2), (0.0, 0.5, 2), (0.0, 0.51, 0), (1.0, 1.0, 0)],
)
def test_affinity_thresholds(tiny_orders, min_support, min_confidence, expected_count):
    assert len(products.affinity_rules(tiny_orders, min_support, min_confidence)) == expected_count


@pytest.mark.parametrize(("min_support", "min_confidence"), [(-0.1, 0.0), (1.1, 0.0), (0.0, -1.0), (0.0, 2.0)])
def test_affinity_rejects_bad_thresholds(tiny_orders, min_support, min_confidence):
    with pytest.raises(ValueError, match="must be within"):
        products.affinity_rules(tiny_orders, min_support, min_confidence)


def test_affinity_empty():
    assert products.affinity_rules([]) == []


def test_perfect_pair_has_confidence_one():
    orders = [
        make_order("O1", lines=[("A", 1, 1.0), ("B", 1, 1.0)]),
        make_order("O2", lines=[("A", 1, 1.0), ("B", 1, 1.0)]),
        make_order("O3", lines=[("C", 1, 1.0)]),
        make_order("O4", lines=[("D", 1, 1.0)]),
    ]
    rules = products.affinity_rules(orders)
    assert [(r.antecedent, r.consequent, r.confidence, r.lift) for r in rules] == [
        ("A", "B", 1.0, 2.0),
        ("B", "A", 1.0, 2.0),
    ]
    assert rules[0].as_dict()["support"] == 0.5


def test_bundled_pairs_dominate_rules_on_generated_data(medium_dataset):
    position = {p.sku: i for i, p in enumerate(medium_dataset.products)}
    rules = products.affinity_rules(medium_dataset.orders, min_support=0.002)[:20]
    assert rules
    bundled = sum(1 for r in rules if position[r.antecedent] ^ 1 == position[r.consequent])
    assert bundled / len(rules) >= 0.8


def test_affinity_lift_symmetry(medium_dataset):
    rules = products.affinity_rules(medium_dataset.orders, min_support=0.002)
    lift = {(r.antecedent, r.consequent): r.lift for r in rules}
    for (a, b), value in lift.items():
        assert lift[(b, a)] == pytest.approx(value, abs=1e-5)
