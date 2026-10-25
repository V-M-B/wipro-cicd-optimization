from __future__ import annotations

from datetime import date

import pytest

from app.generated.schemas import Category, OrderStatus
from app.metrics import revenue
from tests.factories import make_order, make_product


def test_total_revenue_excludes_unpaid_and_cancelled(tiny_orders):
    assert revenue.total_revenue(tiny_orders) == 450.0


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (None, 600.0),
        ({OrderStatus.DELIVERED}, 290.0),
        ({OrderStatus.CANCELLED}, 100.0),
        ({OrderStatus.CREATED, OrderStatus.PAID}, 120.0),
        (set(), 0.0),
    ],
)
def test_total_revenue_with_custom_statuses(tiny_orders, statuses, expected):
    assert revenue.total_revenue(tiny_orders, statuses) == expected


def test_gross_revenue_and_discount(tiny_orders):
    assert revenue.gross_revenue(tiny_orders) == 460.0
    assert revenue.total_discount(tiny_orders) == 10.0


def test_average_order_value(tiny_orders):
    assert revenue.average_order_value(tiny_orders) == 75.0


def test_average_order_value_empty_is_zero():
    assert revenue.average_order_value([]) == 0.0


def test_units_sold(tiny_orders):
    assert revenue.units_sold(tiny_orders) == 15


@pytest.mark.parametrize(
    ("granularity", "expected"),
    [
        ("month", {"2025-01": 230.0, "2025-02": 70.0, "2025-03": 150.0}),
        ("week", {"2025-W02": 140.0, "2025-W03": 90.0, "2025-W06": 70.0, "2025-W09": 150.0}),
        (
            "day",
            {
                "2025-01-06": 120.0,
                "2025-01-07": 20.0,
                "2025-01-15": 90.0,
                "2025-02-03": 70.0,
                "2025-03-01": 120.0,
                "2025-03-02": 30.0,
            },
        ),
    ],
)
def test_revenue_by_period(tiny_orders, granularity, expected):
    result = revenue.revenue_by_period(tiny_orders, granularity)
    assert result == expected
    assert list(result) == sorted(result)


def test_revenue_by_week_fill_gaps(tiny_orders):
    result = revenue.revenue_by_period(tiny_orders, "week", fill_gaps=True)
    assert list(result) == [f"2025-W{w:02d}" for w in range(2, 10)]
    assert result["2025-W04"] == 0.0
    assert sum(result.values()) == 450.0


def test_revenue_by_period_explicit_window(tiny_orders):
    result = revenue.revenue_by_period(
        tiny_orders, "month", fill_gaps=True, start=date(2024, 12, 1), end=date(2025, 2, 28)
    )
    assert result == {"2024-12": 0.0, "2025-01": 230.0, "2025-02": 70.0}


def test_revenue_by_period_window_excludes_outside_orders(tiny_orders):
    result = revenue.revenue_by_period(tiny_orders, "day", start=date(2025, 3, 1), end=date(2025, 3, 1))
    assert result == {"2025-03-01": 120.0}


def test_revenue_by_period_fill_gaps_empty():
    assert revenue.revenue_by_period([], "day", fill_gaps=True) == {}


def test_revenue_by_period_rejects_bad_granularity(tiny_orders):
    with pytest.raises(ValueError, match="granularity"):
        revenue.revenue_by_period(tiny_orders, "quarter")


def test_revenue_by_region(tiny_orders, tiny_customers):
    assert revenue.revenue_by_region(tiny_orders, tiny_customers) == {
        "EAST": 70.0,
        "NORTH": 330.0,
        "SOUTH": 20.0,
        "UNKNOWN": 30.0,
    }


def test_revenue_by_region_without_customers_is_all_unknown(tiny_orders):
    assert revenue.revenue_by_region(tiny_orders, []) == {"UNKNOWN": 450.0}


def test_revenue_by_tier(tiny_orders, tiny_customers):
    assert revenue.revenue_by_tier(tiny_orders, tiny_customers) == {
        "GOLD": 330.0,
        "SILVER": 70.0,
        "STANDARD": 20.0,
        "UNKNOWN": 30.0,
    }


def test_revenue_by_category(tiny_orders, tiny_products):
    assert revenue.revenue_by_category(tiny_orders, tiny_products) == {
        "APPAREL": 90.0,
        "ELECTRONICS": 260.0,
        "GROCERY": 70.0,
        "UNKNOWN": 30.0,
    }


def test_revenue_by_category_allocates_coupon_discount():
    order = make_order("O1", lines=[("A", 1, 60.0), ("B", 1, 40.0)], total=80.0, coupon="VIP20")
    products = [make_product("A", Category.TOYS), make_product("B", Category.HOME)]
    assert revenue.revenue_by_category([order], products) == {"HOME": 32.0, "TOYS": 48.0}


def test_revenue_by_category_lineless_order_is_unassigned():
    order = make_order("O1", lines=[], total=15.0)
    assert revenue.revenue_by_category([order], []) == {"UNASSIGNED": 15.0}


def test_aov_by_region(tiny_orders, tiny_customers):
    assert revenue.aov_by_region(tiny_orders, tiny_customers) == {
        "EAST": 70.0,
        "NORTH": 110.0,
        "SOUTH": 20.0,
        "UNKNOWN": 30.0,
    }


def test_coupon_usage(tiny_orders):
    assert revenue.coupon_usage(tiny_orders) == {"SAVE10": {"orders": 1, "revenue": 90.0, "discount": 10.0}}


def test_coupon_usage_ignores_cancelled_coupons():
    orders = [
        make_order("O1", status="CANCELLED", lines=[("A", 1, 10.0)], total=9.0, coupon="SAVE10"),
        make_order("O2", lines=[("A", 2, 10.0)], total=19.0, coupon="WELCOME5"),
    ]
    assert revenue.coupon_usage(orders) == {"WELCOME5": {"orders": 1, "revenue": 19.0, "discount": 1.0}}


def test_coupon_usage_normalises_codes():
    orders = [
        make_order("O1", lines=[("A", 1, 10.0)], total=9.0, coupon="SAVE10"),
        make_order("O2", lines=[("A", 2, 10.0)], total=18.0, coupon=" save10 "),
        make_order("O3", lines=[("A", 1, 10.0)], total=10.0, coupon="   "),
    ]
    assert revenue.coupon_usage(orders) == {"SAVE10": {"orders": 2, "revenue": 27.0, "discount": 3.0}}


@pytest.mark.parametrize(
    ("breakdown", "expected"),
    [
        ({"a": 1.0, "b": 3.0}, {"a": 0.25, "b": 0.75}),
        ({"a": 0.0, "b": 0.0}, {"a": 0.0, "b": 0.0}),
        ({"x": 2.0}, {"x": 1.0}),
        ({"a": 1.0, "b": 1.0, "c": 1.0}, {"a": 0.3333, "b": 0.3333, "c": 0.3333}),
    ],
)
def test_revenue_share(breakdown, expected):
    assert revenue.revenue_share(breakdown) == expected


def test_revenue_summary(tiny_orders, tiny_customers, tiny_products):
    summary = revenue.revenue_summary(tiny_orders, tiny_customers, tiny_products)
    assert summary["total_revenue"] == 450.0
    assert summary["order_count"] == 6
    assert summary["units_sold"] == 15
    assert summary["average_order_value"] == 75.0
    assert summary["by_period"] == {"2025-01": 230.0, "2025-02": 70.0, "2025-03": 150.0}
    assert sum(summary["by_category"].values()) == pytest.approx(450.0)


def test_breakdowns_reconcile_on_generated_data(medium_dataset):
    ds = medium_dataset
    total = revenue.total_revenue(ds.orders)
    for breakdown in (
        revenue.revenue_by_region(ds.orders, ds.customers),
        revenue.revenue_by_category(ds.orders, ds.products),
        revenue.revenue_by_tier(ds.orders, ds.customers),
        revenue.revenue_by_period(ds.orders, "month"),
    ):
        assert sum(breakdown.values()) == pytest.approx(total, abs=0.01 * len(breakdown))


def test_generated_data_has_no_unknown_buckets(medium_dataset):
    ds = medium_dataset
    assert "UNKNOWN" not in revenue.revenue_by_region(ds.orders, ds.customers)
    assert "UNKNOWN" not in revenue.revenue_by_category(ds.orders, ds.products)
