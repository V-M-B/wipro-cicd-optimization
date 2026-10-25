"""Order status funnel: CREATED -> PAID -> SHIPPED -> DELIVERED, plus cancellations.

``Order.status`` is the *current* state, so an order that is DELIVERED has also
passed through CREATED, PAID and SHIPPED. CANCELLED orders are assumed to have
been cancelled before payment: they reach CREATED only.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass

from app.generated.schemas import Customer, Order, OrderStatus
from app.metrics.common import UNKNOWN, check_granularity, index_customers, order_day, period_key, safe_div

FUNNEL_STAGES: tuple[OrderStatus, ...] = (
    OrderStatus.CREATED,
    OrderStatus.PAID,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
)
_STAGE_INDEX = {stage: i for i, stage in enumerate(FUNNEL_STAGES)}


@dataclass(frozen=True)
class FunnelStage:
    stage: str
    reached: int
    conversion_from_previous: float
    conversion_from_start: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def status_counts(orders: Iterable[Order]) -> dict[str, int]:
    counts = {status.value: 0 for status in OrderStatus}
    for o in orders:
        counts[o.status.value] += 1
    return counts


def stage_reach(counts: dict[str, int]) -> dict[str, int]:
    """Number of orders that reached at least each funnel stage."""
    reach = {stage.value: 0 for stage in FUNNEL_STAGES}
    for status_value, count in counts.items():
        status = OrderStatus(status_value)
        depth = _STAGE_INDEX.get(status, 0)  # CANCELLED -> CREATED only
        for stage in FUNNEL_STAGES[: depth + 1]:
            reach[stage.value] += count
    return reach


def funnel(orders: Iterable[Order]) -> list[FunnelStage]:
    reach = stage_reach(status_counts(orders))
    start = reach[FUNNEL_STAGES[0].value]
    stages: list[FunnelStage] = []
    previous = start
    for stage in FUNNEL_STAGES:
        reached = reach[stage.value]
        stages.append(
            FunnelStage(
                stage=stage.value,
                reached=reached,
                conversion_from_previous=round(safe_div(reached, previous), 4),
                conversion_from_start=round(safe_div(reached, start), 4),
            )
        )
        previous = reached
    return stages


def cancellation_rate(orders: Iterable[Order]) -> float:
    counts = status_counts(orders)
    total = sum(counts.values())
    return round(safe_div(counts[OrderStatus.CANCELLED.value], total), 4)


def bottleneck(stages: list[FunnelStage]) -> str | None:
    """Stage with the lowest conversion from its previous stage (first stage excluded)."""
    candidates = [s for s in stages[1:] if stages[0].reached > 0]
    if not candidates:
        return None
    return min(candidates, key=lambda s: (s.conversion_from_previous, _STAGE_INDEX[OrderStatus(s.stage)])).stage


def funnel_by_region(orders: Iterable[Order], customers: Iterable[Customer]) -> dict[str, list[FunnelStage]]:
    by_id = index_customers(customers)
    groups: dict[str, list[Order]] = defaultdict(list)
    for o in orders:
        customer = by_id.get(o.customerId)
        groups[customer.region.value if customer else UNKNOWN].append(o)
    return {region: funnel(group) for region, group in sorted(groups.items())}


def cancellation_by_period(orders: Iterable[Order], granularity: str = "month") -> dict[str, float]:
    check_granularity(granularity)
    totals: dict[str, int] = defaultdict(int)
    cancelled: dict[str, int] = defaultdict(int)
    for o in orders:
        key = period_key(order_day(o), granularity)
        totals[key] += 1
        if o.status is OrderStatus.CANCELLED:
            cancelled[key] += 1
    return {key: round(cancelled[key] / totals[key], 4) for key in sorted(totals)}
