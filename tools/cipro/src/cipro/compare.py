"""Paired comparison of two workflows over the same commits."""
from __future__ import annotations

from .metrics import RunMetrics, bootstrap_ci, median, percentile

METRICS = [
    ("wall_clock_s", "Wall-clock (s)"),
    ("time_to_first_job_s", "Time to first job (s)"),
    ("job_seconds", "Compute used (job-seconds)"),
    ("billable_min", "Billable minutes"),
    ("cost_usd", "Cost per run (USD)"),
]


def pair(a_runs: list[RunMetrics], b_runs: list[RunMetrics]) -> list[tuple[RunMetrics, RunMetrics]]:
    """Pair by head_sha. If a sha ran several times, keep the latest run of each workflow."""
    def latest(runs):
        out: dict[str, RunMetrics] = {}
        for r in sorted(runs, key=lambda r: r.created_at):
            out[r.head_sha] = r
        return out

    la, lb = latest(a_runs), latest(b_runs)
    return [(la[s], lb[s]) for s in sorted(set(la) & set(lb))]


def compare(a_runs: list[RunMetrics], b_runs: list[RunMetrics], seed: int = 20261025) -> dict:
    pairs = pair(a_runs, b_runs)
    rows = []
    for attr, label in METRICS:
        xs = [(getattr(a, attr), getattr(b, attr)) for a, b in pairs
              if getattr(a, attr) is not None and getattr(b, attr) is not None]
        if not xs:
            continue
        a_vals, b_vals = [x for x, _ in xs], [y for _, y in xs]
        diff, lo, hi = bootstrap_ci(a_vals, b_vals, seed=seed)
        a50 = median(a_vals)
        rows.append({
            "metric": attr, "label": label, "n_pairs": len(xs),
            "a_p50": a50, "a_p95": percentile(a_vals, 95),
            "b_p50": median(b_vals), "b_p95": percentile(b_vals, 95),
            "diff_p50": diff, "diff_ci95": [lo, hi],
            "reduction_pct": (-diff / a50 * 100) if a50 else None,
        })
    return {"pairs": len(pairs), "shas": [a.head_sha for a, _ in pairs], "rows": rows}


def fmt(v, metric: str) -> str:
    if v is None:
        return "n/a"
    if metric == "cost_usd":
        return f"${v:.4f}"
    if metric == "billable_min":
        return f"{v:.1f}"
    return f"{v:,.0f}"


def to_markdown(result: dict, a_name: str, b_name: str) -> str:
    lines = [
        f"Paired comparison on **{result['pairs']}** commits: `{a_name}` (A) vs `{b_name}` (B).",
        "",
        "| Metric | A p50 | A p95 | B p50 | B p95 | Δ p50 (B−A) | 95% CI | Reduction |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in result["rows"]:
        m = r["metric"]
        lo, hi = r["diff_ci95"]
        red = f"{r['reduction_pct']:.1f}%" if r["reduction_pct"] is not None else "n/a"
        lines.append(
            f"| {r['label']} | {fmt(r['a_p50'], m)} | {fmt(r['a_p95'], m)} | {fmt(r['b_p50'], m)} | "
            f"{fmt(r['b_p95'], m)} | {fmt(r['diff_p50'], m)} | [{fmt(lo, m)}, {fmt(hi, m)}] | {red} |"
        )
    lines.append("")
    lines.append("CI: paired bootstrap of the median difference, 5000 resamples, fixed seed.")
    return "\n".join(lines)
