from __future__ import annotations

from datetime import date

import pytest

from app.metrics import customers
from tests.factories import make_order

AS_OF = date(2025, 3, 31)


@pytest.mark.parametrize(
    ("values", "higher_is_better", "expected"),
    [
        ([], True, []),
        ([5], True, [1]),
        ([1, 2, 3, 4, 5], True, [1, 2, 3, 4, 5]),
        ([5, 4, 3, 2, 1], True, [5, 4, 3, 2, 1]),
        ([7, 7, 7], True, [1, 1, 1]),
        (list(range(1, 11)), True, [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]),
        ([1, 2, 3, 4, 5], False, [5, 4, 3, 2, 1]),
        ([1, 1, 2, 2], True, [1, 1, 3, 3]),
        ([10, 0, 5], True, [4, 1, 2]),
        ([0.5, 0.25], False, [1, 3]),
    ],
)
def test_quintile_scores(values, higher_is_better, expected):
    assert customers.quintile_scores(values, higher_is_better=higher_is_better) == expected


def test_quintile_scores_bounds_on_generated_data(medium_dataset):
    values = [o.total for o in medium_dataset.orders]
    scores = customers.quintile_scores(values)
    assert min(scores) == 1
    assert max(scores) == 5
    for score in range(1, 6):
        assert abs(scores.count(score) / len(scores) - 0.2) < 0.02


def test_customer_stats(tiny_orders):
    stats = customers.customer_stats(tiny_orders, AS_OF)
    assert list(stats) == ["C1", "C2", "C3", "C9"]
    c1 = stats["C1"]
    assert (c1.first_order, c1.last_order, c1.frequency, c1.monetary) == (
        date(2025, 1, 6),
        date(2025, 3, 1),
        3,
        330.0,
    )


def test_customer_stats_respects_as_of(tiny_orders):
    stats = customers.customer_stats(tiny_orders, date(2025, 1, 31))
    assert set(stats) == {"C1", "C2"}
    assert stats["C1"].frequency == 2


def test_rfm_scores_tiny(tiny_orders):
    records = {r.customer_id: r for r in customers.rfm_scores(tiny_orders, AS_OF)}
    assert {cid: (r.recency_days, r.frequency, r.monetary) for cid, r in records.items()} == {
        "C1": (30, 3, 330.0),
        "C2": (83, 1, 20.0),
        "C3": (56, 1, 70.0),
        "C9": (29, 1, 30.0),
    }
    assert {cid: r.code for cid, r in records.items()} == {"C1": "344", "C2": "111", "C3": "213", "C9": "412"}
    assert {cid: r.segment for cid, r in records.items()} == {
        "C1": "Loyal",
        "C2": "Lost",
        "C3": "Hibernating",
        "C9": "Promising",
    }


def test_rfm_record_as_dict_includes_code(tiny_orders):
    record = customers.rfm_scores(tiny_orders, AS_OF)[0]
    data = record.as_dict()
    assert data["code"] == "344"
    assert data["customer_id"] == "C1"


def test_rfm_excludes_customers_without_revenue(tiny_orders):
    ids = {r.customer_id for r in customers.rfm_scores(tiny_orders, AS_OF)}
    assert "C4" not in ids  # only has a CREATED (unpaid) order


def test_rfm_empty():
    assert customers.rfm_scores([], AS_OF) == []


def test_recency_is_days_since_last_order():
    orders = [make_order("O1", "A", day="2025-03-01"), make_order("O2", "A", day="2025-03-21")]
    (record,) = customers.rfm_scores(orders, AS_OF)
    assert record.recency_days == 10
    assert record.frequency == 2


def test_rfm_on_generated_data_has_valid_scores(medium_dataset, as_of):
    records = customers.rfm_scores(medium_dataset.orders, as_of)
    assert records
    for r in records:
        assert 1 <= r.r <= 5
        assert 1 <= r.f <= 5
        assert 1 <= r.m <= 5
        assert r.recency_days >= 0
        assert r.segment in customers.SEGMENTS


def test_higher_monetary_never_scores_lower(medium_dataset, as_of):
    records = sorted(customers.rfm_scores(medium_dataset.orders, as_of), key=lambda r: r.monetary)
    m_scores = [r.m for r in records]
    assert m_scores == sorted(m_scores)


def test_more_recent_never_scores_lower(medium_dataset, as_of):
    records = sorted(customers.rfm_scores(medium_dataset.orders, as_of), key=lambda r: -r.recency_days)
    r_scores = [r.r for r in records]
    assert r_scores == sorted(r_scores)


def test_segment_counts(tiny_orders):
    counts = customers.segment_counts(customers.rfm_scores(tiny_orders, AS_OF))
    assert list(counts) == list(customers.SEGMENTS)
    assert counts["Loyal"] == 1
    assert counts["Lost"] == 1
    assert counts["Champions"] == 0
    assert sum(counts.values()) == 4
