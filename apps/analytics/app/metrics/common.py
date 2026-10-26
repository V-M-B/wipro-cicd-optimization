"""Helpers shared by the metric modules: periods, status sets, allocation, rounding."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from app.generated.schemas import Customer, Order, OrderStatus, Product

Granularity = Literal["day", "week", "month", "quarter"]
GRANULARITIES: tuple[str, ...] = ("day", "week", "month", "quarter")

#: Statuses that count as recognised revenue (payment captured).
REVENUE_STATUSES: frozenset[OrderStatus] = frozenset({OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED})
#: Statuses that count as customer activity (everything except cancellations).
ACTIVE_STATUSES: frozenset[OrderStatus] = frozenset(OrderStatus) - {OrderStatus.CANCELLED}

UNKNOWN = "UNKNOWN"
UNASSIGNED = "UNASSIGNED"


def money(value: float) -> float:
    """Round a monetary amount to cents (and normalise -0.0 to 0.0)."""
    rounded = round(value, 2)
    return 0.0 if rounded == 0 else rounded


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    return numerator / denominator if denominator else default


def order_day(order: Order) -> date:
    """Calendar day of an order in UTC (naive datetimes are treated as UTC)."""
    created: datetime = order.createdAt
    if created.tzinfo is not None:
        created = created.astimezone(UTC)
    return created.date()


def check_granularity(granularity: str) -> None:
    if granularity not in GRANULARITIES:
        raise ValueError(f"granularity must be one of {', '.join(GRANULARITIES)}; got {granularity!r}")


def period_start(day: date, granularity: str) -> date:
    """First day of the period containing ``day``."""
    check_granularity(granularity)
    if granularity == "day":
        return day
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    if granularity == "quarter":
        return date(day.year, _quarter_first_month(day.month), 1)
    return day.replace(day=1)


def _quarter_first_month(month: int) -> int:
    return 3 * ((month - 1) // 3) + 1


def period_key(day: date, granularity: str) -> str:
    """Stable, sortable label: ``2025-03-07`` / ``2025-W10`` (ISO week) / ``2025-03`` / ``2025-Q1``."""
    check_granularity(granularity)
    if granularity == "day":
        return day.isoformat()
    if granularity == "week":
        iso_year, iso_week, _ = day.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if granularity == "quarter":
        return f"{day.year:04d}-Q{(day.month - 1) // 3 + 1}"
    return f"{day.year:04d}-{day.month:02d}"


def next_period_start(start: date, granularity: str) -> date:
    check_granularity(granularity)
    if granularity == "day":
        return start + timedelta(days=1)
    if granularity == "week":
        return start + timedelta(days=7)
    step = 3 if granularity == "quarter" else 1
    month_index0 = start.year * 12 + (start.month - 1) + step
    return date(month_index0 // 12, month_index0 % 12 + 1, 1)


def period_range(start: date, end: date, granularity: str) -> list[str]:
    """All period keys covering ``start``..``end`` inclusive, in chronological order."""
    if end < start:
        raise ValueError("end must not be before start")
    keys: list[str] = []
    cursor = period_start(start, granularity)
    while cursor <= end:
        keys.append(period_key(cursor, granularity))
        cursor = next_period_start(cursor, granularity)
    return keys


def month_index(day: date) -> int:
    """Months since year 0, so that consecutive months differ by exactly one."""
    return day.year * 12 + (day.month - 1)


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def filter_status(orders: Iterable[Order], statuses: Iterable[OrderStatus] | None) -> list[Order]:
    """Orders whose status is in ``statuses`` (``None`` keeps everything)."""
    if statuses is None:
        return list(orders)
    allowed = frozenset(statuses)
    return [o for o in orders if o.status in allowed]


def line_gross(quantity: int, unit_price: float) -> float:
    return quantity * unit_price


def order_gross(order: Order) -> float:
    return sum(line_gross(line.quantity, line.unitPrice) for line in order.lines)


def allocate_order_total(order: Order) -> list[tuple[str, float]]:
    """Split ``order.total`` over its lines in proportion to line gross value.

    The allocated amounts always sum to ``order.total`` (up to float error), so any
    grouping of allocated line revenue reconciles with order-level revenue. Orders
    without lines are allocated to :data:`UNASSIGNED`; zero-value lines share evenly.
    """
    if not order.lines:
        return [(UNASSIGNED, order.total)]
    grosses = [line_gross(line.quantity, line.unitPrice) for line in order.lines]
    gross_total = sum(grosses)
    if gross_total <= 0:
        share = order.total / len(order.lines)
        return [(line.sku, share) for line in order.lines]
    return [(line.sku, order.total * g / gross_total) for line, g in zip(order.lines, grosses, strict=True)]


def index_customers(customers: Iterable[Customer]) -> dict[str, Customer]:
    return {c.id: c for c in customers}


def index_products(products: Iterable[Product]) -> dict[str, Product]:
    """Products keyed by SKU (the key used on order lines)."""
    return {p.sku: p for p in products}


def sorted_by_value(mapping: dict[str, float], *, descending: bool = True) -> list[tuple[str, float]]:
    """Items sorted by value (ties broken by key ascending for determinism)."""
    sign = -1 if descending else 1
    return sorted(mapping.items(), key=lambda kv: (sign * kv[1], kv[0]))
