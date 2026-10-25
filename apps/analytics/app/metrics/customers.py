"""Customer metrics: RFM scores and segments, cohort retention, churn, CLV.

Every function that depends on "now" takes an explicit ``as_of`` date; orders
created after ``as_of`` are ignored so results are reproducible.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date

from app.generated.schemas import Order, OrderStatus
from app.metrics.common import (
    ACTIVE_STATUSES,
    REVENUE_STATUSES,
    filter_status,
    money,
    month_index,
    month_label,
    order_day,
    safe_div,
)

Statuses = Iterable[OrderStatus] | None
RETENTION_MODES = ("active", "rolling")

SEGMENTS = (
    "Champions",
    "Loyal",
    "New",
    "Promising",
    "Can't Lose Them",
    "At Risk",
    "Needs Attention",
    "Hibernating",
    "Lost",
)


@dataclass(frozen=True)
class CustomerStats:
    customer_id: str
    first_order: date
    last_order: date
    frequency: int
    monetary: float


@dataclass(frozen=True)
class RFMRecord:
    customer_id: str
    recency_days: int
    frequency: int
    monetary: float
    r: int
    f: int
    m: int
    segment: str

    @property
    def code(self) -> str:
        return f"{self.r}{self.f}{self.m}"

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["code"] = self.code
        return data


@dataclass
class RetentionMatrix:
    mode: str
    cohorts: list[str] = field(default_factory=list)
    sizes: list[int] = field(default_factory=list)
    rows: list[list[float]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"mode": self.mode, "cohorts": self.cohorts, "sizes": self.sizes, "rows": self.rows}

    def row(self, cohort: str) -> list[float]:
        return self.rows[self.cohorts.index(cohort)]


def _orders_until(orders: Iterable[Order], as_of: date | None, statuses: Statuses) -> list[Order]:
    selected = filter_status(orders, statuses)
    if as_of is None:
        return selected
    return [o for o in selected if order_day(o) <= as_of]


def customer_stats(
    orders: Iterable[Order], as_of: date | None = None, statuses: Statuses = REVENUE_STATUSES
) -> dict[str, CustomerStats]:
    first: dict[str, date] = {}
    last: dict[str, date] = {}
    freq: dict[str, int] = defaultdict(int)
    spend: dict[str, float] = defaultdict(float)
    for o in _orders_until(orders, as_of, statuses):
        day = order_day(o)
        cid = o.customerId
        if cid not in first or day < first[cid]:
            first[cid] = day
        if cid not in last or day > last[cid]:
            last[cid] = day
        freq[cid] += 1
        spend[cid] += o.total
    return {cid: CustomerStats(cid, first[cid], last[cid], freq[cid], money(spend[cid])) for cid in sorted(first)}


def quintile_scores(values: Sequence[float], *, higher_is_better: bool = True) -> list[int]:
    """Rank-based 1..5 scores. Equal values always receive equal scores.

    score = 1 + floor(5 * (#values strictly worse) / n).
    """
    n = len(values)
    if n == 0:
        return []
    keyed = [v if higher_is_better else -v for v in values]
    ordered = sorted(keyed)
    return [1 + (bisect.bisect_left(ordered, v) * 5) // n for v in keyed]


def rfm_segment(r: int, f: int, m: int) -> str:
    """Map 1..5 R/F/M scores to a named segment (rules evaluated top to bottom)."""
    for name, score in (("r", r), ("f", f), ("m", m)):
        if not 1 <= score <= 5:
            raise ValueError(f"{name} score must be within 1..5; got {score}")
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Loyal"
    if r == 5 and f == 1:
        return "New"
    if r >= 4:
        return "Promising"
    if r <= 2 and f >= 4:
        return "Can't Lose Them"
    if r <= 2 and f == 3:
        return "At Risk"
    if r == 3:
        return "Needs Attention"
    if r == 2:
        return "Hibernating"
    return "Lost"


def rfm_scores(orders: Iterable[Order], as_of: date, statuses: Statuses = REVENUE_STATUSES) -> list[RFMRecord]:
    """RFM record per customer with at least one qualifying order on or before ``as_of``."""
    stats = list(customer_stats(orders, as_of, statuses).values())
    recency = [(as_of - s.last_order).days for s in stats]
    r_scores = quintile_scores(recency, higher_is_better=False)
    f_scores = quintile_scores([s.frequency for s in stats])
    m_scores = quintile_scores([s.monetary for s in stats])
    records = []
    for s, rec, r, f, m in zip(stats, recency, r_scores, f_scores, m_scores, strict=True):
        records.append(
            RFMRecord(
                customer_id=s.customer_id,
                recency_days=rec,
                frequency=s.frequency,
                monetary=s.monetary,
                r=r,
                f=f,
                m=m,
                segment=rfm_segment(r, f, m),
            )
        )
    return records


def segment_counts(records: Iterable[RFMRecord]) -> dict[str, int]:
    counts = dict.fromkeys(SEGMENTS, 0)
    for rec in records:
        counts[rec.segment] += 1
    return counts


def cohort_retention(
    orders: Iterable[Order],
    mode: str = "active",
    *,
    end: date | None = None,
    statuses: Statuses = ACTIVE_STATUSES,
) -> RetentionMatrix:
    """Monthly acquisition-cohort retention matrix.

    A customer's cohort is the month of their first qualifying order. Row ``c``,
    column ``k`` is the fraction of cohort ``c`` that

    * ``active``: placed an order in month ``c + k``;
    * ``rolling``: placed an order in month ``c + k`` or later (non-increasing in k).

    Columns run up to the last month with data (or ``end``), so the matrix is triangular.
    """
    if mode not in RETENTION_MODES:
        raise ValueError(f"mode must be one of {', '.join(RETENTION_MODES)}; got {mode!r}")
    months_by_customer: dict[str, set[int]] = defaultdict(set)
    for o in _orders_until(orders, end, statuses):
        months_by_customer[o.customerId].add(month_index(order_day(o)))
    matrix = RetentionMatrix(mode=mode)
    if not months_by_customer:
        return matrix
    last_month = month_index(end) if end is not None else max(max(m) for m in months_by_customer.values())
    cohorts: dict[int, list[set[int]]] = defaultdict(list)
    for months in months_by_customer.values():
        cohorts[min(months)].append(months)
    for cohort in sorted(cohorts):
        members = cohorts[cohort]
        size = len(members)
        row: list[float] = []
        for offset in range(last_month - cohort + 1):
            target = cohort + offset
            if mode == "active":
                hits = sum(1 for months in members if target in months)
            else:
                hits = sum(1 for months in members if max(months) >= target)
            row.append(round(hits / size, 4))
        matrix.cohorts.append(month_label(cohort))
        matrix.sizes.append(size)
        matrix.rows.append(row)
    return matrix


def average_retention_curve(matrix: RetentionMatrix) -> list[float]:
    """Cohort-size-weighted mean retention per month offset."""
    if not matrix.rows:
        return []
    width = max(len(r) for r in matrix.rows)
    curve = []
    for k in range(width):
        num = sum(row[k] * size for row, size in zip(matrix.rows, matrix.sizes, strict=True) if len(row) > k)
        den = sum(size for row, size in zip(matrix.rows, matrix.sizes, strict=True) if len(row) > k)
        curve.append(round(safe_div(num, den), 4))
    return curve


def churn_flags(
    orders: Iterable[Order],
    as_of: date,
    threshold_days: int = 90,
    statuses: Statuses = ACTIVE_STATUSES,
) -> dict[str, bool]:
    """True for customers whose last order is more than ``threshold_days`` before ``as_of``."""
    if threshold_days < 0:
        raise ValueError("threshold_days must be >= 0")
    stats = customer_stats(orders, as_of, statuses)
    return {cid: (as_of - s.last_order).days > threshold_days for cid, s in stats.items()}


def churn_rate(flags: dict[str, bool]) -> float:
    return round(safe_div(sum(flags.values()), len(flags)), 4)


def monthly_retention_rate(
    orders: Iterable[Order], end: date | None = None, statuses: Statuses = ACTIVE_STATUSES
) -> float:
    """Mean share of customers active in month m who are also active in month m+1."""
    active: dict[int, set[str]] = defaultdict(set)
    for o in _orders_until(orders, end, statuses):
        active[month_index(order_day(o))].add(o.customerId)
    if not active:
        return 0.0
    months = range(min(active), max(active))
    rates = [len(active[m] & active[m + 1]) / len(active[m]) for m in months if active[m]]
    return round(safe_div(sum(rates), len(rates)), 4)


def clv_formula(margin_per_period: float, retention: float, discount_rate: float) -> float:
    """Infinite-horizon CLV with constant retention: m * r / (1 + d - r)."""
    if not 0.0 <= retention < 1.0:
        raise ValueError("retention must be within [0, 1)")
    if discount_rate < 0.0:
        raise ValueError("discount_rate must be >= 0")
    return margin_per_period * retention / (1.0 + discount_rate - retention)


def customer_clv(
    orders: Sequence[Order],
    as_of: date,
    gross_margin: float = 0.3,
    retention: float | None = None,
    discount_rate: float = 0.01,
) -> dict[str, float]:
    """Predicted CLV per customer from their average monthly margin since first order."""
    if not 0.0 <= gross_margin <= 1.0:
        raise ValueError("gross_margin must be within [0, 1]")
    if retention is None:
        retention = min(monthly_retention_rate(orders, as_of), 0.99)
    stats = customer_stats(orders, as_of)
    result: dict[str, float] = {}
    for cid, s in stats.items():
        months_observed = month_index(as_of) - month_index(s.first_order) + 1
        monthly_margin = s.monetary * gross_margin / months_observed
        result[cid] = money(clv_formula(monthly_margin, retention, discount_rate))
    return result
