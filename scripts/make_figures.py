"""Dissertation figures as standalone SVG (standard library only), generated from cipro data.

Usage: python scripts/make_figures.py --out docs/dissertation/figures
Figures (each skipped if its data is not available yet):
  fig1-wallclock-strip.svg      wall-clock per run, one row per workflow, replay commits only
  fig2-paired-reduction.svg     median paired wall-clock difference vs baseline with 95% bootstrap CI
  fig3-time-vs-billable.svg     median wall-clock vs median billable minutes per workflow (speed/cost trade-off)
  fig4-tests-by-category.svg    share of baseline tests executed by the TIA stage, per change category
  fig5-shard-curve.svg          wall-clock and billable minutes vs shard count (if shard-count runs exist)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/cipro/src"))
from cipro import store  # noqa: E402
from cipro.compare import compare  # noqa: E402
from cipro.metrics import workflow_runs  # noqa: E402

PALETTE = {"ci-baseline.yml": "#6b7280", "ci-cache.yml": "#2563eb", "ci-parallel.yml": "#d97706",
           "ci-optimized.yml": "#059669", "ci-ephemeral.yml": "#7c3aed"}
LABEL = {"ci-baseline.yml": "Baseline", "ci-cache.yml": "Cache", "ci-parallel.yml": "Parallel + shards",
         "ci-optimized.yml": "Parallel + shards + TIA", "ci-ephemeral.yml": "Ephemeral runners"}
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"


def svg(w, h, body):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {FONT}>"
            f"<rect width='100%' height='100%' fill='white'/>{body}</svg>")


def text(x, y, s, size=12, anchor="start", color="#111827", weight="normal"):
    return (f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' text-anchor='{anchor}' fill='{color}' "
            f"font-weight='{weight}'>{escape(str(s))}</text>")


def rounds_for(wf):
    return {"ci-cache.yml": ["a"], "ci-optimized.yml": ["a"], "ci-parallel.yml": ["b"],
            "ci-baseline.yml": ["a", "b"], "ci-ephemeral.yml": ["e"]}[wf]


def load(con, wf, rnd):
    return workflow_runs(con, wf, branch_glob=f"exp/{rnd}/*")


def fig1(con, out):
    rows = []
    for wf in PALETTE:
        vals = [r.wall_clock_s / 60 for rnd in rounds_for(wf) for r in load(con, wf, rnd) if r.wall_clock_s]
        if vals:
            rows.append((wf, vals))
    if not rows:
        return None
    W, H, L, R, T, B = 760, 70 + 46 * len(rows), 190, 30, 40, 40
    xmax = max(max(v) for _, v in rows) * 1.05
    X = lambda m: L + (W - L - R) * m / xmax  # noqa: E731
    body = text(L, 24, "Wall-clock per run on replay commits (minutes)", 14, weight="bold")
    for i, (wf, vals) in enumerate(rows):
        y = T + 20 + i * 46
        body += text(L - 10, y + 4, f"{LABEL[wf]} (n={len(vals)})", 12, "end")
        for k, v in enumerate(sorted(vals)):
            jitter = ((k * 7) % 11 - 5) * 1.4
            body += f"<circle cx='{X(v):.1f}' cy='{y + jitter:.1f}' r='3' fill='{PALETTE[wf]}' fill-opacity='0.55'/>"
        med = statistics.median(vals)
        body += f"<line x1='{X(med):.1f}' x2='{X(med):.1f}' y1='{y - 14}' y2='{y + 14}' stroke='#111827' stroke-width='2'/>"
        body += text(X(med) + 4, y - 16, f"p50 {med:.1f}", 10, color="#374151")
    yb = H - B + 6
    body += f"<line x1='{L}' x2='{W - R}' y1='{yb}' y2='{yb}' stroke='#9ca3af'/>"
    step = 5 if xmax > 15 else 1
    m = 0
    while m <= xmax:
        body += f"<line x1='{X(m):.1f}' x2='{X(m):.1f}' y1='{yb}' y2='{yb + 4}' stroke='#9ca3af'/>" + text(X(m), yb + 16, m, 10, "middle")
        m += step
    (out / "fig1-wallclock-strip.svg").write_text(svg(W, H, body), encoding="utf-8")
    return "fig1-wallclock-strip.svg"


def paired(con):
    res = []
    for wf, rnd in (("ci-cache.yml", "a"), ("ci-parallel.yml", "b"), ("ci-optimized.yml", "a")):
        base = load(con, "ci-baseline.yml", rnd)
        stage = load(con, wf, rnd)
        c = compare(base, stage)
        if not c["pairs"]:
            continue
        rows = {r["metric"]: r for r in c["rows"]}
        res.append((wf, c["pairs"], rows))
    return res


def fig2(con, out):
    data = paired(con)
    if not data:
        return None
    W, H, L, R, T = 880, 100 + 56 * len(data), 210, 190, 50
    lo = min(min(r["wall_clock_s"]["diff_ci95"][0], r["wall_clock_s"]["diff_p50"]) for _, _, r in data)
    hi = max(max(r["wall_clock_s"]["diff_ci95"][1], r["wall_clock_s"]["diff_p50"], 0) for _, _, r in data)
    span = (hi - lo) or 1
    lo, hi = lo - 0.05 * span, hi + 0.05 * span
    X = lambda s: L + (W - L - R) * (s - lo) / (hi - lo)  # noqa: E731
    body = text(20, 24, "Median paired wall-clock difference vs baseline (seconds, 95% bootstrap CI)", 14, weight="bold")
    body += text(W - R + 12, T - 6, "Δ p50 (reduction)", 11, color="#6b7280")
    for i, (wf, n, rows) in enumerate(data):
        r = rows["wall_clock_s"]
        y = T + 24 + i * 56
        a, b = r["diff_ci95"]
        d = r["diff_p50"]
        body += text(L - 10, y + 4, f"{LABEL[wf]} (n={n})", 12, "end")
        x0, x1 = sorted((X(0), X(d)))
        body += f"<rect x='{x0:.1f}' y='{y - 9}' width='{x1 - x0:.1f}' height='18' fill='{PALETTE[wf]}' fill-opacity='0.75'/>"
        body += f"<line x1='{X(a):.1f}' x2='{X(b):.1f}' y1='{y}' y2='{y}' stroke='#111827' stroke-width='2'/>"
        for e in (a, b):
            body += f"<line x1='{X(e):.1f}' x2='{X(e):.1f}' y1='{y - 6}' y2='{y + 6}' stroke='#111827' stroke-width='2'/>"
        red = r["reduction_pct"]
        body += text(W - R + 12, y + 4, f"{d:+.0f} s ({'n/a' if red is None else f'{red:.1f}%'})", 11, color="#374151")
    body += f"<line x1='{X(0):.1f}' x2='{X(0):.1f}' y1='{T}' y2='{H - 34}' stroke='#9ca3af'/>" + text(X(0), H - 18, "0 = baseline", 10, "middle")
    body += text(L, H - 18, f"{lo:.0f} s", 10, "start", "#6b7280") + text(W - R, H - 18, f"{hi:+.0f} s", 10, "end", "#6b7280")
    (out / "fig2-paired-reduction.svg").write_text(svg(W, H, body), encoding="utf-8")
    return "fig2-paired-reduction.svg"


def fig3(con, out):
    pts = []
    for wf in PALETTE:
        runs = [r for rnd in rounds_for(wf) for r in load(con, wf, rnd)]
        if runs:
            pts.append((wf, statistics.median(r.wall_clock_s for r in runs) / 60,
                        statistics.median(r.billable_min for r in runs),
                        statistics.mean(r.billable_min for r in runs)))
    if not pts:
        return None
    W, H, L, R, T, B = 640, 420, 70, 30, 50, 60
    xmax = max(p[1] for p in pts) * 1.25
    ymax = max(max(p[2], p[3]) for p in pts) * 1.25
    X = lambda v: L + (W - L - R) * v / xmax  # noqa: E731
    Y = lambda v: H - B - (H - T - B) * v / ymax  # noqa: E731
    body = text(L, 26, "Speed vs cost: median wall-clock vs billable minutes", 14, weight="bold")
    body += text(L, 42, "filled: median billable minutes · ring: mean billable minutes", 10, color="#6b7280")
    body += f"<line x1='{L}' x2='{W - R}' y1='{H - B}' y2='{H - B}' stroke='#9ca3af'/><line x1='{L}' x2='{L}' y1='{T}' y2='{H - B}' stroke='#9ca3af'/>"
    body += text((L + W - R) / 2, H - 18, "median wall-clock (minutes)", 11, "middle")
    body += f"<text x='18' y='{(T + H - B) / 2:.0f}' font-size='11' transform='rotate(-90 18 {(T + H - B) / 2:.0f})' text-anchor='middle'>billable minutes per run</text>"
    for i in range(0, int(xmax) + 1):
        body += text(X(i), H - B + 14, i, 10, "middle")
    for j in range(0, int(ymax) + 1, max(1, int(ymax / 6))):
        body += text(L - 6, Y(j) + 3, j, 10, "end")
    for wf, x, ymed, ymean in pts:
        body += f"<circle cx='{X(x):.1f}' cy='{Y(ymed):.1f}' r='7' fill='{PALETTE[wf]}'/>"
        body += f"<circle cx='{X(x):.1f}' cy='{Y(ymean):.1f}' r='7' fill='none' stroke='{PALETTE[wf]}' stroke-width='2'/>"
        body += text(X(x) + 11, Y(ymed) + 4, LABEL[wf], 11)
    (out / "fig3-time-vs-billable.svg").write_text(svg(W, H, body), encoding="utf-8")
    return "fig3-time-vs-billable.svg"


def fig4(out):
    files = sorted((ROOT / "experiments/results").glob("tia-ci-a-*.json"))
    if not files:
        return None
    data = json.loads(files[-1].read_text(encoding="utf-8"))["summary"]
    cats = [(c, s["tests_executed_share_median"]) for c, s in data.items() if s["tests_executed_share_median"] is not None]
    if not cats:
        return None
    W, H, L, R, T = 640, 80 + 36 * len(cats), 120, 60, 46
    X = lambda v: L + (W - L - R) * v  # noqa: E731
    body = text(L, 24, "Tests executed by the TIA stage, share of the baseline's tests (median per category)", 13, weight="bold")
    for i, (c, v) in enumerate(cats):
        y = T + 16 + i * 36
        body += text(L - 10, y + 4, c, 12, "end")
        body += f"<rect x='{L}' y='{y - 10}' width='{X(1) - L:.1f}' height='20' fill='#e5e7eb'/>"
        body += f"<rect x='{L}' y='{y - 10}' width='{X(v) - L:.1f}' height='20' fill='{PALETTE['ci-optimized.yml']}'/>"
        body += text(X(v) + 6 if v < 0.85 else X(v) - 6, y + 4, f"{v * 100:.0f}%", 11, "start" if v < 0.85 else "end",
                     "#111827" if v < 0.85 else "white")
    body += text(L, H - 12, f"Source: {files[-1].relative_to(ROOT).as_posix()}", 9, color="#6b7280")
    (out / "fig4-tests-by-category.svg").write_text(svg(W, H, body), encoding="utf-8")
    return "fig4-tests-by-category.svg"


def fig5(out):
    files = sorted((ROOT / "experiments/results").glob("shard-curve-*.json"))
    if not files:
        return None
    pts = json.loads(files[-1].read_text(encoding="utf-8"))["points"]  # [{shards, wall_p50_s, billable_p50}]
    W, H, L, R, T, B = 640, 380, 70, 70, 50, 56
    xs = [p["shards"] for p in pts]
    wmax = max(p["wall_p50_s"] for p in pts) / 60 * 1.2
    bmax = max(p["billable_p50"] for p in pts) * 1.2
    X = lambda v: L + (W - L - R) * (xs.index(v)) / max(1, len(xs) - 1)  # noqa: E731
    YW = lambda v: H - B - (H - T - B) * v / wmax  # noqa: E731
    YB = lambda v: H - B - (H - T - B) * v / bmax  # noqa: E731
    body = text(L, 26, "Shard count: wall-clock falls, billable minutes rise", 14, weight="bold")
    body += f"<line x1='{L}' x2='{W - R}' y1='{H - B}' y2='{H - B}' stroke='#9ca3af'/>"
    pw = " ".join(f"{X(p['shards']):.1f},{YW(p['wall_p50_s'] / 60):.1f}" for p in pts)
    pb = " ".join(f"{X(p['shards']):.1f},{YB(p['billable_p50']):.1f}" for p in pts)
    body += f"<polyline points='{pw}' fill='none' stroke='{PALETTE['ci-parallel.yml']}' stroke-width='2.5'/>"
    body += f"<polyline points='{pb}' fill='none' stroke='#6b7280' stroke-width='2.5' stroke-dasharray='6 4'/>"
    for p in pts:
        body += f"<circle cx='{X(p['shards']):.1f}' cy='{YW(p['wall_p50_s'] / 60):.1f}' r='4' fill='{PALETTE['ci-parallel.yml']}'/>"
        body += f"<circle cx='{X(p['shards']):.1f}' cy='{YB(p['billable_p50']):.1f}' r='4' fill='#6b7280'/>"
        body += text(X(p["shards"]), H - B + 16, p["shards"], 11, "middle")
    body += text((L + W - R) / 2, H - 16, "shards per sharded suite", 11, "middle")
    body += text(L, T - 4, "— wall-clock p50 (min)", 10, color=PALETTE["ci-parallel.yml"])
    body += text(W - R, T - 4, "- - billable minutes p50", 10, "end", "#6b7280")
    (out / "fig5-shard-curve.svg").write_text(svg(W, H, body), encoding="utf-8")
    return "fig5-shard-curve.svg"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/dissertation/figures")
    ap.add_argument("--db", default=str(ROOT / "experiments/results/cipro.sqlite"))
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    con = store.connect(a.db)
    made = [f for f in (fig1(con, out), fig2(con, out), fig3(con, out), fig4(out), fig5(out)) if f]
    print("wrote:", ", ".join(made) if made else "nothing (no data yet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
