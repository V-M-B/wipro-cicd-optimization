"""Time-series helpers: moving averages, smoothing, growth and anomaly detection.

All functions take plain sequences of floats so they can be applied to any
metric series (daily revenue, order counts, ...).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from app.generated.schemas import Order, OrderStatus
from app.metrics.common import REVENUE_STATUSES, filter_status, order_day, period_key


@dataclass(frozen=True)
class Anomaly:
    index: int
    value: float
    score: float | None  # z-score / fence distance; None when the baseline has zero variance
    direction: str  # "high" or "low"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _check_window(window: int) -> None:
    if window < 1:
        raise ValueError("window must be >= 1")


def _check_alpha(name: str, value: float) -> None:
    if not 0.0 < value <= 1.0:
        raise ValueError(f"{name} must be within (0, 1]")


def simple_moving_average(values: Sequence[float], window: int) -> list[float | None]:
    """Trailing mean of the last ``window`` values; ``None`` until the window is full."""
    _check_window(window)
    out: list[float | None] = []
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= window:
            running -= values[i - window]
        out.append(running / window if i >= window - 1 else None)
    return out


def weighted_moving_average(values: Sequence[float], window: int) -> list[float | None]:
    """Linearly weighted trailing mean (most recent value has weight ``window``)."""
    _check_window(window)
    denom = window * (window + 1) / 2
    out: list[float | None] = []
    for i in range(len(values)):
        if i < window - 1:
            out.append(None)
            continue
        chunk = values[i - window + 1 : i + 1]
        out.append(sum(w * v for w, v in enumerate(chunk, start=1)) / denom)
    return out


def exponential_smoothing(values: Sequence[float], alpha: float) -> list[float]:
    """Simple exponential smoothing: s0 = x0, s_t = alpha*x_t + (1-alpha)*s_{t-1}."""
    _check_alpha("alpha", alpha)
    out: list[float] = []
    level = 0.0
    for i, v in enumerate(values):
        level = v if i == 0 else alpha * v + (1 - alpha) * level
        out.append(level)
    return out


def holt_linear(
    values: Sequence[float], alpha: float, beta: float, horizon: int = 0
) -> tuple[list[float], list[float]]:
    """Holt's double exponential smoothing. Returns (fitted levels, forecasts)."""
    _check_alpha("alpha", alpha)
    _check_alpha("beta", beta)
    if horizon < 0:
        raise ValueError("horizon must be >= 0")
    if not values:
        return [], []
    if len(values) == 1:
        return [float(values[0])], [float(values[0])] * horizon
    level = float(values[0])
    trend = float(values[1] - values[0])
    fitted = [level]
    for v in values[1:]:
        prev_level = level
        level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
        fitted.append(level)
    forecast = [level + (h + 1) * trend for h in range(horizon)]
    return fitted, forecast


def pct_change(values: Sequence[float], lag: int = 1) -> list[float | None]:
    """Relative change vs ``lag`` steps earlier; ``None`` where undefined (start or zero base)."""
    if lag < 1:
        raise ValueError("lag must be >= 1")
    out: list[float | None] = []
    for i, v in enumerate(values):
        if i < lag or values[i - lag] == 0:
            out.append(None)
        else:
            out.append((v - values[i - lag]) / abs(values[i - lag]))
    return out


def daily_series(mapping: Mapping[date, float], start: date, end: date) -> list[float]:
    """Dense list of daily values from ``start`` to ``end`` (missing days -> 0.0)."""
    if end < start:
        raise ValueError("end must not be before start")
    days = (end - start).days + 1
    return [float(mapping.get(start + timedelta(days=i), 0.0)) for i in range(days)]


def daily_revenue(
    orders: Iterable[Order], statuses: Iterable[OrderStatus] | None = REVENUE_STATUSES
) -> dict[date, float]:
    totals: dict[date, float] = {}
    for o in filter_status(orders, statuses):
        day = order_day(o)
        totals[day] = totals.get(day, 0.0) + o.total
    return dict(sorted(totals.items()))


def weekly_totals(daily: Mapping[date, float]) -> dict[str, float]:
    """Aggregate daily values into ISO weeks (chronological keys)."""
    totals: dict[str, float] = {}
    for day in sorted(daily):
        key = period_key(day, "week")
        totals[key] = totals.get(key, 0.0) + daily[day]
    return totals


def week_over_week(daily: Mapping[date, float]) -> list[dict[str, object]]:
    """Weekly totals with growth vs the previous calendar week (missing weeks count as 0)."""
    if not daily:
        return []
    first = min(daily)
    last = max(daily)
    first -= timedelta(days=first.weekday())
    weekly = weekly_totals(daily)
    rows: list[dict[str, object]] = []
    previous: float | None = None
    cursor = first
    while cursor <= last:
        key = period_key(cursor, "week")
        total = round(weekly.get(key, 0.0), 2)
        growth = None if previous in (None, 0) else round((total - previous) / previous, 4)  # type: ignore[operator]
        rows.append({"week": key, "total": total, "growth": growth})
        previous = total
        cursor += timedelta(days=7)
    return rows


def mean_std(values: Sequence[float]) -> tuple[float, float]:
    """Mean and population standard deviation."""
    n = len(values)
    if n == 0:
        raise ValueError("values must not be empty")
    mean = math.fsum(values) / n
    var = math.fsum((v - mean) ** 2 for v in values) / n
    return mean, math.sqrt(var)


def zscores(values: Sequence[float]) -> list[float]:
    mean, std = mean_std(values)
    if std == 0:
        return [0.0] * len(values)
    return [(v - mean) / std for v in values]


def zscore_anomalies(values: Sequence[float], threshold: float = 3.0) -> list[Anomaly]:
    """Points whose absolute z-score is strictly greater than ``threshold``."""
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    if not values:
        return []
    out = []
    for i, z in enumerate(zscores(values)):
        if abs(z) > threshold:
            out.append(Anomaly(i, float(values[i]), round(z, 6), "high" if z > 0 else "low"))
    return out


def quantile(values: Sequence[float], q: float) -> float:
    """Quantile with linear interpolation between closest ranks (NumPy's default)."""
    if not values:
        raise ValueError("values must not be empty")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be within [0, 1]")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(ordered[lo])
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def iqr_bounds(values: Sequence[float], k: float = 1.5) -> tuple[float, float]:
    """Tukey fences (Q1 - k*IQR, Q3 + k*IQR)."""
    if k < 0:
        raise ValueError("k must be >= 0")
    q1 = quantile(values, 0.25)
    q3 = quantile(values, 0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def iqr_anomalies(values: Sequence[float], k: float = 1.5) -> list[Anomaly]:
    """Points strictly outside the Tukey fences. ``score`` is the distance to the fence."""
    if not values:
        return []
    low, high = iqr_bounds(values, k)
    out = []
    for i, v in enumerate(values):
        if v > high:
            out.append(Anomaly(i, float(v), round(v - high, 6), "high"))
        elif v < low:
            out.append(Anomaly(i, float(v), round(low - v, 6), "low"))
    return out


def rolling_zscore_anomalies(values: Sequence[float], window: int = 7, threshold: float = 3.0) -> list[Anomaly]:
    """Compare each point with the mean/std of the ``window`` points before it.

    Points whose trailing window has zero variance are flagged only if they
    differ from that constant level.
    """
    _check_window(window)
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    out = []
    for i in range(window, len(values)):
        mean, std = mean_std(values[i - window : i])
        v = values[i]
        if std == 0:
            if v != mean:
                out.append(Anomaly(i, float(v), None, "high" if v > mean else "low"))
            continue
        z = (v - mean) / std
        if abs(z) > threshold:
            out.append(Anomaly(i, float(v), round(z, 6), "high" if z > 0 else "low"))
    return out
