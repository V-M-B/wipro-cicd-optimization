from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.generated.schemas import Order, OrderStatus
from app.metrics import common
from tests.factories import make_order


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.0, 0.0), (-0.0, 0.0), (-0.001, 0.0), (1.005, 1.0), (2.675, 2.67), (10.129, 10.13), (-3.456, -3.46)],
)
def test_money_rounds_to_cents(value, expected):
    result = common.money(value)
    assert result == expected
    assert str(result) != "-0.0"


@pytest.mark.parametrize(("num", "den", "expected"), [(1, 2, 0.5), (5, 0, 0.0), (0, 0, 0.0), (-3, 4, -0.75)])
def test_safe_div(num, den, expected):
    assert common.safe_div(num, den) == expected


def test_safe_div_custom_default():
    assert common.safe_div(1, 0, default=-1.0) == -1.0


@pytest.mark.parametrize(
    ("day", "granularity", "expected"),
    [
        (date(2025, 3, 7), "day", "2025-03-07"),
        (date(2025, 3, 7), "week", "2025-W10"),
        (date(2025, 3, 7), "month", "2025-03"),
        (date(2024, 12, 30), "week", "2025-W01"),  # ISO year differs from calendar year
        (date(2021, 1, 3), "week", "2020-W53"),
        (date(2026, 12, 31), "week", "2026-W53"),
        (date(2025, 12, 1), "month", "2025-12"),
    ],
)
def test_period_key(day, granularity, expected):
    assert common.period_key(day, granularity) == expected


@pytest.mark.parametrize(
    ("day", "granularity", "expected"),
    [
        (date(2025, 3, 7), "day", date(2025, 3, 7)),
        (date(2025, 3, 7), "week", date(2025, 3, 3)),
        (date(2025, 3, 3), "week", date(2025, 3, 3)),
        (date(2025, 3, 9), "week", date(2025, 3, 3)),
        (date(2025, 3, 31), "month", date(2025, 3, 1)),
    ],
)
def test_period_start(day, granularity, expected):
    assert common.period_start(day, granularity) == expected


@pytest.mark.parametrize(
    ("start", "granularity", "expected"),
    [
        (date(2025, 1, 31), "day", date(2025, 2, 1)),
        (date(2025, 12, 29), "week", date(2026, 1, 5)),
        (date(2025, 11, 1), "month", date(2025, 12, 1)),
        (date(2025, 12, 1), "month", date(2026, 1, 1)),
    ],
)
def test_next_period_start(start, granularity, expected):
    assert common.next_period_start(start, granularity) == expected


@pytest.mark.parametrize(
    ("start", "end", "granularity", "expected"),
    [
        (date(2025, 1, 30), date(2025, 2, 2), "day", ["2025-01-30", "2025-01-31", "2025-02-01", "2025-02-02"]),
        (date(2025, 1, 1), date(2025, 1, 1), "day", ["2025-01-01"]),
        (date(2025, 1, 1), date(2025, 1, 20), "week", ["2025-W01", "2025-W02", "2025-W03", "2025-W04"]),
        (date(2025, 11, 15), date(2026, 2, 1), "month", ["2025-11", "2025-12", "2026-01", "2026-02"]),
        (date(2024, 12, 28), date(2025, 1, 6), "week", ["2024-W52", "2025-W01", "2025-W02"]),
    ],
)
def test_period_range(start, end, granularity, expected):
    assert common.period_range(start, end, granularity) == expected


def test_period_range_rejects_reversed_range():
    with pytest.raises(ValueError, match="end must not be before start"):
        common.period_range(date(2025, 2, 1), date(2025, 1, 1), "day")


@pytest.mark.parametrize("bad", ["year", "DAY", "", "quarter"])
def test_invalid_granularity(bad):
    with pytest.raises(ValueError, match="granularity"):
        common.period_key(date(2025, 1, 1), bad)


@pytest.mark.parametrize(
    ("day", "expected"),
    [(date(2025, 1, 1), 2025 * 12), (date(2025, 12, 31), 2025 * 12 + 11), (date(2026, 1, 1), 2026 * 12)],
)
def test_month_index(day, expected):
    assert common.month_index(day) == expected
    assert common.month_label(expected) == f"{day.year:04d}-{day.month:02d}"


def test_order_day_converts_aware_datetimes_to_utc():
    ist = timezone(timedelta(hours=5, minutes=30))
    order = make_order("O1")
    late_utc = order.model_copy(update={"createdAt": datetime(2025, 1, 1, 23, 30, tzinfo=UTC)})
    early_ist = order.model_copy(update={"createdAt": datetime(2025, 1, 2, 3, 0, tzinfo=ist)})
    assert common.order_day(late_utc) == date(2025, 1, 1)
    assert common.order_day(early_ist) == date(2025, 1, 1)


def test_filter_status_none_keeps_all(tiny_orders):
    assert common.filter_status(tiny_orders, None) == tiny_orders


def test_filter_status_revenue(tiny_orders):
    kept = common.filter_status(tiny_orders, common.REVENUE_STATUSES)
    assert [o.id for o in kept] == ["O1", "O2", "O3", "O4", "O7", "O8"]


def test_status_sets():
    assert OrderStatus.CREATED not in common.REVENUE_STATUSES
    assert OrderStatus.CANCELLED not in common.ACTIVE_STATUSES
    assert common.REVENUE_STATUSES < common.ACTIVE_STATUSES


@pytest.mark.parametrize(
    ("lines", "total", "expected"),
    [
        ([("A", 1, 100.0)], 100.0, [("A", 100.0)]),
        ([("A", 1, 100.0), ("B", 1, 100.0)], 180.0, [("A", 90.0), ("B", 90.0)]),
        ([("A", 3, 10.0), ("B", 1, 10.0)], 36.0, [("A", 27.0), ("B", 9.0)]),
        ([("A", 1, 0.0), ("B", 1, 0.0)], 10.0, [("A", 5.0), ("B", 5.0)]),
        ([], 12.5, [(common.UNASSIGNED, 12.5)]),
    ],
)
def test_allocate_order_total(lines, total, expected):
    order = make_order("O1", lines=lines, total=total)
    allocated = common.allocate_order_total(order)
    assert [sku for sku, _ in allocated] == [sku for sku, _ in expected]
    assert [amount for _, amount in allocated] == pytest.approx([amount for _, amount in expected])


def test_allocation_reconciles_for_generated_orders(small_dataset):
    for o in small_dataset.orders:
        assert sum(amount for _, amount in common.allocate_order_total(o)) == pytest.approx(o.total)


def test_order_gross(tiny_orders):
    grosses = {o.id: common.order_gross(o) for o in tiny_orders}
    assert grosses["O1"] == 120.0
    assert grosses["O3"] == 100.0


def test_indexes(tiny_customers, tiny_products):
    assert set(common.index_customers(tiny_customers)) == {"C1", "C2", "C3", "C4"}
    assert common.index_products(tiny_products)["GRO-1"].unitPrice == 10.0


def test_sorted_by_value_breaks_ties_by_key():
    data = {"b": 1.0, "a": 1.0, "c": 3.0}
    assert common.sorted_by_value(data) == [("c", 3.0), ("a", 1.0), ("b", 1.0)]
    assert common.sorted_by_value(data, descending=False) == [("a", 1.0), ("b", 1.0), ("c", 3.0)]


def test_orders_are_shared_schema_models(tiny_orders):
    assert all(isinstance(o, Order) for o in tiny_orders)
