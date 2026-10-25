"""Product metrics: per-SKU sales, top-N, ABC (Pareto) classes, basket affinity."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations

from app.generated.schemas import Order, OrderStatus, Product
from app.metrics.common import (
    REVENUE_STATUSES,
    UNASSIGNED,
    allocate_order_total,
    filter_status,
    index_products,
    money,
)

Statuses = Iterable[OrderStatus] | None
RANK_BY = ("revenue", "units", "orders")


@dataclass(frozen=True)
class ProductSales:
    sku: str
    name: str
    category: str
    units: int
    revenue: float
    orders: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AffinityRule:
    antecedent: str
    consequent: str
    count: int
    support: float
    confidence: float
    lift: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def product_sales(
    orders: Iterable[Order],
    products: Iterable[Product] = (),
    statuses: Statuses = REVENUE_STATUSES,
) -> dict[str, ProductSales]:
    """Units, allocated revenue and order count per SKU (SKUs absent from the catalogue are kept)."""
    catalogue = index_products(products)
    units: dict[str, int] = defaultdict(int)
    revenue: dict[str, float] = defaultdict(float)
    order_count: dict[str, int] = defaultdict(int)
    for o in filter_status(orders, statuses):
        seen: set[str] = set()
        for line in o.lines:
            units[line.sku] += line.quantity
            if line.sku not in seen:
                order_count[line.sku] += 1
                seen.add(line.sku)
        for sku, amount in allocate_order_total(o):
            if sku != UNASSIGNED:
                revenue[sku] += amount
    result: dict[str, ProductSales] = {}
    for sku in sorted(units):
        product = catalogue.get(sku)
        result[sku] = ProductSales(
            sku=sku,
            name=product.name if product else sku,
            category=product.category.value if product else "UNKNOWN",
            units=units[sku],
            revenue=money(revenue[sku]),
            orders=order_count[sku],
        )
    return result


def top_products(
    orders: Iterable[Order],
    products: Iterable[Product] = (),
    n: int = 10,
    by: str = "revenue",
    statuses: Statuses = REVENUE_STATUSES,
) -> list[ProductSales]:
    """Best ``n`` SKUs ranked by revenue, units or orders (ties: SKU ascending)."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if by not in RANK_BY:
        raise ValueError(f"by must be one of {', '.join(RANK_BY)}; got {by!r}")
    sales = list(product_sales(orders, products, statuses).values())
    sales.sort(key=lambda s: (-getattr(s, by), s.sku))
    return sales[:n]


def abc_classification(values: Mapping[str, float], a: float = 0.8, b: float = 0.95) -> dict[str, str]:
    """Pareto ABC classes from contribution values.

    Items are sorted by value descending (ties: key ascending). An item is ``A``
    while the cumulative share *before* it is below ``a``, ``B`` while it is below
    ``b``, otherwise ``C``. Items with zero (or negative) value are always ``C``.
    """
    if not 0.0 < a < b <= 1.0:
        raise ValueError("thresholds must satisfy 0 < a < b <= 1")
    positive_total = sum(v for v in values.values() if v > 0)
    ordered = sorted(values.items(), key=lambda kv: (-kv[1], kv[0]))
    classes: dict[str, str] = {}
    cumulative = 0.0
    for key, value in ordered:
        if value <= 0 or positive_total <= 0:
            classes[key] = "C"
            continue
        share_before = cumulative / positive_total
        if share_before < a:
            classes[key] = "A"
        elif share_before < b:
            classes[key] = "B"
        else:
            classes[key] = "C"
        cumulative += value
    return classes


def abc_for_products(
    orders: Iterable[Order],
    products: Sequence[Product] = (),
    a: float = 0.8,
    b: float = 0.95,
    include_unsold: bool = True,
) -> dict[str, str]:
    sales = product_sales(orders, products)
    values = {sku: s.revenue for sku, s in sales.items()}
    if include_unsold:
        for p in products:
            values.setdefault(p.sku, 0.0)
    return abc_classification(values, a, b)


def abc_summary(classes: Mapping[str, str], values: Mapping[str, float]) -> dict[str, dict[str, float]]:
    """Count and revenue share for each ABC class."""
    total = sum(v for v in values.values() if v > 0)
    summary = {cls: {"count": 0, "share": 0.0} for cls in ("A", "B", "C")}
    for key, cls in classes.items():
        summary[cls]["count"] += 1
        summary[cls]["share"] += max(values.get(key, 0.0), 0.0)
    for cls in summary:
        summary[cls]["share"] = round(summary[cls]["share"] / total, 4) if total else 0.0
    return summary


def basket_skus(order: Order) -> frozenset[str]:
    return frozenset(line.sku for line in order.lines)


def co_occurrence(orders: Iterable[Order], statuses: Statuses = None) -> dict[tuple[str, str], int]:
    """Number of orders containing each unordered SKU pair (pair keys are sorted tuples)."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for o in filter_status(orders, statuses):
        for pair in combinations(sorted(basket_skus(o)), 2):
            counts[pair] += 1
    return dict(sorted(counts.items()))


def affinity_rules(
    orders: Iterable[Order],
    min_support: float = 0.01,
    min_confidence: float = 0.0,
    statuses: Statuses = None,
) -> list[AffinityRule]:
    """Pairwise association rules ``A -> B`` with support, confidence and lift.

    support = P(A and B), confidence = P(B | A), lift = confidence / P(B).
    Sorted by lift, then confidence (both descending), then antecedent/consequent.
    """
    if not 0.0 <= min_support <= 1.0:
        raise ValueError("min_support must be within [0, 1]")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be within [0, 1]")
    selected = filter_status(orders, statuses)
    baskets = [basket_skus(o) for o in selected]
    n = len(baskets)
    if n == 0:
        return []
    single: dict[str, int] = defaultdict(int)
    pairs: dict[tuple[str, str], int] = defaultdict(int)
    for basket in baskets:
        for sku in basket:
            single[sku] += 1
        for pair in combinations(sorted(basket), 2):
            pairs[pair] += 1
    rules: list[AffinityRule] = []
    for (x, y), count in pairs.items():
        support = count / n
        if support < min_support:
            continue
        for ante, cons in ((x, y), (y, x)):
            confidence = count / single[ante]
            if confidence < min_confidence:
                continue
            lift = confidence / (single[cons] / n)
            rules.append(
                AffinityRule(
                    antecedent=ante,
                    consequent=cons,
                    count=count,
                    support=round(support, 6),
                    confidence=round(confidence, 6),
                    lift=round(lift, 6),
                )
            )
    rules.sort(key=lambda r: (-r.lift, -r.confidence, r.antecedent, r.consequent))
    return rules


def frequently_bought_with(orders: Iterable[Order], sku: str, n: int = 5) -> list[tuple[str, int]]:
    """SKUs most often in the same basket as ``sku`` (ties: SKU ascending)."""
    if n < 0:
        raise ValueError("n must be >= 0")
    counts: dict[str, int] = defaultdict(int)
    for o in orders:
        basket = basket_skus(o)
        if sku in basket:
            for other in basket:
                if other != sku:
                    counts[other] += 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def category_unit_mix(
    orders: Iterable[Order], products: Iterable[Product], statuses: Statuses = REVENUE_STATUSES
) -> dict[str, float]:
    """Share of units sold per category (rounded to 4 decimals)."""
    catalogue = index_products(products)
    units: dict[str, int] = defaultdict(int)
    for o in filter_status(orders, statuses):
        for line in o.lines:
            product = catalogue.get(line.sku)
            units[product.category.value if product else "UNKNOWN"] += line.quantity
    total = sum(units.values())
    return {k: round(v / total, 4) for k, v in sorted(units.items())} if total else {}
