"""Revenue metrics: totals, period/region/category/tier breakdowns, AOV, coupons.

Order-level revenue uses ``Order.total`` (after coupon discounts). Line-level
breakdowns (category, product) allocate each order's total over its lines in
proportion to gross line value, so every breakdown reconciles with the total.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date

from app.generated.schemas import Customer, Order, OrderStatus, Product
from app.metrics.common import (
    REVENUE_STATUSES,
    UNASSIGNED,
    UNKNOWN,
    allocate_order_total,
    check_granularity,
    filter_status,
    index_customers,
    index_products,
    money,
    order_day,
    order_gross,
    period_key,
    period_range,
    safe_div,
)

Statuses = Iterable[OrderStatus] | None


def revenue_orders(orders: Iterable[Order], statuses: Statuses = REVENUE_STATUSES) -> list[Order]:
    return filter_status(orders, statuses)


def total_revenue(orders: Iterable[Order], statuses: Statuses = REVENUE_STATUSES) -> float:
    return money(sum(o.total for o in revenue_orders(orders, statuses)))


def gross_revenue(orders: Iterable[Order], statuses: Statuses = REVENUE_STATUSES) -> float:
    """Revenue before coupon discounts (sum of quantity x unit price)."""
    return money(sum(order_gross(o) for o in revenue_orders(orders, statuses)))


def total_discount(orders: Iterable[Order], statuses: Statuses = REVENUE_STATUSES) -> float:
    selected = revenue_orders(orders, statuses)
    return money(sum(order_gross(o) - o.total for o in selected))


def average_order_value(orders: Iterable[Order], statuses: Statuses = REVENUE_STATUSES) -> float:
    selected = revenue_orders(orders, statuses)
    return money(safe_div(sum(o.total for o in selected), len(selected)))


def units_sold(orders: Iterable[Order], statuses: Statuses = REVENUE_STATUSES) -> int:
    return sum(line.quantity for o in revenue_orders(orders, statuses) for line in o.lines)


def revenue_by_period(
    orders: Iterable[Order],
    granularity: str = "day",
    *,
    fill_gaps: bool = False,
    start: date | None = None,
    end: date | None = None,
    statuses: Statuses = REVENUE_STATUSES,
) -> dict[str, float]:
    """Revenue per day / ISO week / month, chronologically ordered.

    With ``fill_gaps`` every period between ``start`` (default: first order) and
    ``end`` (default: last order) appears, with 0.0 for periods without revenue.
    Orders outside an explicit ``start``/``end`` window are excluded.
    """
    check_granularity(granularity)
    selected = revenue_orders(orders, statuses)
    if start is not None:
        selected = [o for o in selected if order_day(o) >= start]
    if end is not None:
        selected = [o for o in selected if order_day(o) <= end]
    totals: dict[str, float] = defaultdict(float)
    for o in selected:
        totals[period_key(order_day(o), granularity)] += o.total
    if fill_gaps:
        days = [order_day(o) for o in selected]
        lo = start if start is not None else (min(days) if days else None)
        hi = end if end is not None else (max(days) if days else None)
        if lo is None or hi is None:
            return {}
        return {key: money(totals.get(key, 0.0)) for key in period_range(lo, hi, granularity)}
    return {key: money(totals[key]) for key in sorted(totals)}


def revenue_by_region(
    orders: Iterable[Order],
    customers: Iterable[Customer],
    statuses: Statuses = REVENUE_STATUSES,
) -> dict[str, float]:
    """Revenue per customer region; orders of unknown customers go to ``UNKNOWN``."""
    by_id = index_customers(customers)
    totals: dict[str, float] = defaultdict(float)
    for o in revenue_orders(orders, statuses):
        customer = by_id.get(o.customerId)
        totals[customer.region.value if customer else UNKNOWN] += o.total
    return {key: money(totals[key]) for key in sorted(totals)}


def revenue_by_tier(
    orders: Iterable[Order],
    customers: Iterable[Customer],
    statuses: Statuses = REVENUE_STATUSES,
) -> dict[str, float]:
    by_id = index_customers(customers)
    totals: dict[str, float] = defaultdict(float)
    for o in revenue_orders(orders, statuses):
        customer = by_id.get(o.customerId)
        totals[customer.tier.value if customer else UNKNOWN] += o.total
    return {key: money(totals[key]) for key in sorted(totals)}


def revenue_by_category(
    orders: Iterable[Order],
    products: Iterable[Product],
    statuses: Statuses = REVENUE_STATUSES,
) -> dict[str, float]:
    """Allocated revenue per product category (unknown SKUs go to ``UNKNOWN``)."""
    by_sku = index_products(products)
    totals: dict[str, float] = defaultdict(float)
    for o in revenue_orders(orders, statuses):
        for sku, amount in allocate_order_total(o):
            if sku == UNASSIGNED:
                totals[UNASSIGNED] += amount
                continue
            product = by_sku.get(sku)
            totals[product.category.value if product else UNKNOWN] += amount
    return {key: money(totals[key]) for key in sorted(totals)}


def aov_by_region(
    orders: Iterable[Order],
    customers: Iterable[Customer],
    statuses: Statuses = REVENUE_STATUSES,
) -> dict[str, float]:
    by_id = index_customers(customers)
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for o in revenue_orders(orders, statuses):
        customer = by_id.get(o.customerId)
        key = customer.region.value if customer else UNKNOWN
        sums[key] += o.total
        counts[key] += 1
    return {key: money(sums[key] / counts[key]) for key in sorted(sums)}


def coupon_usage(orders: Iterable[Order], statuses: Statuses = REVENUE_STATUSES) -> dict[str, dict[str, float]]:
    """Per coupon code: number of orders, revenue and discount granted.

    Codes are compared case-insensitively and without surrounding whitespace (``" save10"`` is
    reported as ``"SAVE10"``); blank codes are treated as no coupon.
    """
    stats: dict[str, dict[str, float]] = {}
    for o in revenue_orders(orders, statuses):
        code = (o.couponCode or "").strip().upper()
        if not code:
            continue
        entry = stats.setdefault(code, {"orders": 0, "revenue": 0.0, "discount": 0.0})
        entry["orders"] += 1
        entry["revenue"] += o.total
        entry["discount"] += order_gross(o) - o.total
    return {
        code: {"orders": int(v["orders"]), "revenue": money(v["revenue"]), "discount": money(v["discount"])}
        for code, v in sorted(stats.items())
    }


def revenue_share(breakdown: dict[str, float]) -> dict[str, float]:
    """Fraction of the total contributed by each key (rounded to 4 decimals)."""
    total = sum(breakdown.values())
    if total <= 0:
        return dict.fromkeys(breakdown, 0.0)
    return {key: round(value / total, 4) for key, value in breakdown.items()}


def revenue_summary(
    orders: Sequence[Order],
    customers: Sequence[Customer] = (),
    products: Sequence[Product] = (),
    granularity: str = "month",
) -> dict[str, object]:
    return {
        "total_revenue": total_revenue(orders),
        "gross_revenue": gross_revenue(orders),
        "total_discount": total_discount(orders),
        "order_count": len(revenue_orders(orders)),
        "units_sold": units_sold(orders),
        "average_order_value": average_order_value(orders),
        "by_period": revenue_by_period(orders, granularity),
        "by_region": revenue_by_region(orders, customers),
        "by_category": revenue_by_category(orders, products),
    }
