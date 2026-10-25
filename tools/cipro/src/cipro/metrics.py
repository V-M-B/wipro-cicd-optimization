"""Metrics over stored runs: durations, queue time, billable minutes, cost, critical path, statistics."""
from __future__ import annotations

import json
import math
import random
import sqlite3
import tomllib
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from importlib import resources

from .classify import OVERHEAD, classify


def ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds(start: str | None, end: str | None) -> float | None:
    a, b = ts(start), ts(end)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolated percentile, q in [0, 100]."""
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def median(values: list[float]) -> float | None:
    return percentile(values, 50)


def bootstrap_ci(
    a: list[float], b: list[float], stat=median, n: int = 5000, seed: int = 20261025, alpha: float = 0.05
) -> tuple[float, float, float]:
    """CI for stat(b) - stat(a) over paired samples (resampling pairs)."""
    if len(a) != len(b) or not a:
        raise ValueError("need equal-length, non-empty paired samples")
    rng = random.Random(seed)
    idx = range(len(a))
    point = stat(b) - stat(a)
    diffs = []
    for _ in range(n):
        sample = [rng.choice(idx) for _ in idx]
        diffs.append(stat([b[i] for i in sample]) - stat([a[i] for i in sample]))
    return point, percentile(diffs, 100 * alpha / 2), percentile(diffs, 100 * (1 - alpha / 2))


def load_pricing() -> dict:
    with resources.files("cipro").joinpath("pricing.toml").open("rb") as f:
        return tomllib.load(f)


def rate_for(labels: list[str], pricing: dict, self_hosted_fee: bool) -> float:
    if "self-hosted" in labels or not labels:
        return pricing["self_hosted"]["platform_fee_per_minute_scenario"] if self_hosted_fee else 0.0
    table = pricing["github_hosted"]["per_minute"]
    for label in labels:
        if label in table:
            return table[label]
        if label.startswith("ubuntu"):
            return table["ubuntu-latest"]
        if label.startswith("windows"):
            return table["windows-latest"]
        if label.startswith("macos"):
            return table["macos-latest"]
    return table["ubuntu-latest"]


@dataclass
class JobMetrics:
    id: int
    name: str
    conclusion: str | None
    queue_s: float | None
    duration_s: float | None
    billable_min: int
    labels: list[str]
    started_at: str | None
    completed_at: str | None
    created_at: str | None


@dataclass
class RunMetrics:
    id: int
    workflow: str
    head_sha: str
    head_branch: str
    conclusion: str | None
    created_at: str
    wall_clock_s: float | None          # first job created -> last job completed (includes queueing)
    exec_span_s: float | None           # first job started -> last job completed
    time_to_first_job_s: float | None   # first job created -> first job started
    queue_total_s: float
    job_seconds: float                  # sum of job durations (compute actually used)
    billable_min: int                   # GitHub rule: each job rounded up to a whole minute
    cost_usd: float
    cost_usd_self_hosted_fee: float     # scenario where the self-hosted platform fee applies
    jobs: list[JobMetrics] = field(default_factory=list)
    category_s: dict[str, float] = field(default_factory=dict)
    critical_path: list[str] = field(default_factory=list)

    @property
    def overhead_share(self) -> float | None:
        total = sum(self.category_s.values())
        if not total:
            return None
        return sum(v for k, v in self.category_s.items() if k in OVERHEAD) / total

    def to_dict(self) -> dict:
        d = asdict(self)
        d["overhead_share"] = self.overhead_share
        return d


def critical_path(jobs: list[JobMetrics], slack_s: float = 5.0) -> list[str]:
    """Heuristic critical path: walk back from the last-finishing job through the latest-finishing
    job that completed before the current one started. The API does not expose `needs:` edges."""
    done = [j for j in jobs if j.started_at and j.completed_at and (j.duration_s or 0) > 0]
    if not done:
        return []
    cur = max(done, key=lambda j: ts(j.completed_at))
    path = [cur]
    while True:
        start = ts(cur.started_at)
        preds = [
            j for j in done
            if j is not cur and j not in path and (ts(j.completed_at) - start).total_seconds() <= slack_s
        ]
        if not preds:
            break
        cur = max(preds, key=lambda j: ts(j.completed_at))
        path.append(cur)
    return [j.name for j in reversed(path)]


def run_metrics(con: sqlite3.Connection, run_id: int, pricing: dict | None = None) -> RunMetrics:
    pricing = pricing or load_pricing()
    r = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    jobs_rows = con.execute("SELECT * FROM jobs WHERE run_id=? ORDER BY started_at", (run_id,)).fetchall()
    jobs: list[JobMetrics] = []
    cost = cost_fee = 0.0
    categories: dict[str, float] = defaultdict(float)
    for j in jobs_rows:
        labels = json.loads(j["labels"] or "[]")
        dur = seconds(j["started_at"], j["completed_at"])
        ran = j["conclusion"] not in ("skipped", None) and dur is not None and dur > 0
        billable = math.ceil(dur / 60.0) if ran else 0
        jobs.append(JobMetrics(
            j["id"], j["name"], j["conclusion"], seconds(j["created_at"], j["started_at"]), dur, billable,
            labels, j["started_at"], j["completed_at"], j["created_at"],
        ))
        cost += billable * rate_for(labels, pricing, self_hosted_fee=False)
        cost_fee += billable * rate_for(labels, pricing, self_hosted_fee=True)
        for s in con.execute("SELECT * FROM steps WHERE job_id=?", (j["id"],)):
            d = seconds(s["started_at"], s["completed_at"])
            if d:
                categories[classify(s["name"])] += d
    ran_jobs = [j for j in jobs if j.started_at and j.completed_at]
    created = [ts(j.created_at) for j in ran_jobs if j.created_at]
    started = [ts(j.started_at) for j in ran_jobs]
    completed = [ts(j.completed_at) for j in ran_jobs]
    wall = (max(completed) - min(created)).total_seconds() if created and completed else None
    span = (max(completed) - min(started)).total_seconds() if started else None
    first = (min(started) - min(created)).total_seconds() if created and started else None
    return RunMetrics(
        id=r["id"], workflow=r["workflow"], head_sha=r["head_sha"], head_branch=r["head_branch"],
        conclusion=r["conclusion"], created_at=r["created_at"], wall_clock_s=wall, exec_span_s=span,
        time_to_first_job_s=first,
        queue_total_s=sum(j.queue_s or 0 for j in jobs if j.billable_min),
        job_seconds=sum(j.duration_s or 0 for j in jobs if j.billable_min),
        billable_min=sum(j.billable_min for j in jobs), cost_usd=round(cost, 6),
        cost_usd_self_hosted_fee=round(cost_fee, 6), jobs=jobs, category_s=dict(categories),
        critical_path=critical_path(jobs),
    )


def workflow_runs(
    con: sqlite3.Connection, workflow: str, branch_glob: str | None = None, success_only: bool = True,
    since: str | None = None,
) -> list[RunMetrics]:
    sql = "SELECT id FROM runs WHERE workflow=?"
    args: list = [workflow]
    if success_only:
        sql += " AND conclusion='success'"
    if branch_glob:
        sql += " AND head_branch GLOB ?"
        args.append(branch_glob)
    if since:
        sql += " AND created_at >= ?"
        args.append(since)
    sql += " ORDER BY created_at"
    pricing = load_pricing()
    return [run_metrics(con, row["id"], pricing) for row in con.execute(sql, args).fetchall()]


def summarize(runs: list[RunMetrics]) -> dict:
    def col(attr):
        return [getattr(r, attr) for r in runs if getattr(r, attr) is not None]

    wall = col("wall_clock_s")
    cats: dict[str, list[float]] = defaultdict(list)
    for r in runs:
        for c, v in r.category_s.items():
            cats[c].append(v)
    return {
        "runs": len(runs),
        "wall_clock_p50_s": median(wall),
        "wall_clock_p95_s": percentile(wall, 95),
        "wall_clock_min_s": min(wall) if wall else None,
        "wall_clock_max_s": max(wall) if wall else None,
        "time_to_first_job_p50_s": median(col("time_to_first_job_s")),
        "queue_total_p50_s": median(col("queue_total_s")),
        "job_seconds_p50": median(col("job_seconds")),
        "billable_min_p50": median(col("billable_min")),
        "cost_usd_p50": median(col("cost_usd")),
        "cost_usd_per_1000_runs_p50": (median(col("cost_usd")) or 0) * 1000,
        "overhead_share_p50": median([r.overhead_share for r in runs if r.overhead_share is not None]),
        "category_p50_s": {c: median(v) for c, v in sorted(cats.items())},
    }


def step_stats(con: sqlite3.Connection, run_ids: list[int]) -> list[dict]:
    if not run_ids:
        return []
    q = ",".join("?" * len(run_ids))
    rows = con.execute(
        f"SELECT j.name AS job, s.name AS step, s.started_at, s.completed_at FROM steps s "
        f"JOIN jobs j ON j.id = s.job_id WHERE j.run_id IN ({q})",
        run_ids,
    ).fetchall()
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        d = seconds(row["started_at"], row["completed_at"])
        if d is not None:
            groups[(row["job"], row["step"])].append(d)
    out = [
        {"job": job, "step": step, "category": classify(step), "n": len(v),
         "p50_s": median(v), "p95_s": percentile(v, 95), "mean_s": sum(v) / len(v)}
        for (job, step), v in groups.items()
    ]
    return sorted(out, key=lambda d: d["p50_s"] or 0, reverse=True)
