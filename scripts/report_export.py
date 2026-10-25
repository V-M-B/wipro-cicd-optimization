"""Render a cipro export directory (experiments/results/<label>-<stamp>/) as Markdown tables.

Usage: python scripts/report_export.py experiments/results/phase0-baseline-10runs-20261025T181852Z
Every number comes from the export files; nothing is typed by hand.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mmss(s):
    if s is None or s == "":
        return "n/a"
    s = float(s)
    return f"{int(s // 60)}m {int(round(s % 60)):02d}s"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = Path(sys.argv[1])
    if not d.is_absolute():
        d = ROOT / d
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    print(f"Source export: `{d.relative_to(ROOT).as_posix()}` (label `{meta['label']}`, exported {meta['exported_at']},"
          f" filters: since={meta['since']}, branch={meta['branch_glob']}, failed included={meta['include_failed']})\n")
    for wf in meta["workflows"]:
        s = json.loads((d / f"{wf}.summary.json").read_text(encoding="utf-8"))
        print(f"### `{wf}` — {s['runs']} successful runs\n")
        print("| Metric | Value |\n|---|---:|")
        rows = [
            ("Wall-clock p50", mmss(s["wall_clock_p50_s"])), ("Wall-clock p95", mmss(s["wall_clock_p95_s"])),
            ("Wall-clock min / max", f"{mmss(s['wall_clock_min_s'])} / {mmss(s['wall_clock_max_s'])}"),
            ("Time to first job p50", mmss(s["time_to_first_job_p50_s"])),
            ("Compute used p50 (job-seconds)", f"{s['job_seconds_p50']:.0f} s"),
            ("Billable minutes p50", f"{s['billable_min_p50']:.0f}"),
            ("Cost per run p50 (GitHub-hosted list price)", f"${s['cost_usd_p50']:.3f}"),
            ("Cost per 1000 runs (p50 × 1000)", f"${s['cost_usd_per_1000_runs_p50']:.2f}"),
            ("Wall-clock mean", mmss(s.get("wall_clock_mean_s"))),
            ("Billable minutes mean", f"{s['billable_min_mean']:.1f}" if s.get("billable_min_mean") is not None else "n/a"),
            ("Cost per 1000 runs (mean × 1000)", f"${s['cost_usd_per_1000_runs_mean']:.2f}" if s.get("cost_usd_per_1000_runs_mean") is not None else "n/a"),
            ("Overhead share p50", f"{(s['overhead_share_p50'] or 0) * 100:.1f}%"),
        ]
        for k, v in rows:
            print(f"| {k} | {v} |")
        print("\n**Median step time by category (seconds):**\n")
        cats = s["category_p50_s"]
        total = sum(v for v in cats.values() if v)
        print("| Category | p50 (s) | Share of p50 total |\n|---|---:|---:|")
        for c, v in sorted(cats.items(), key=lambda kv: -(kv[1] or 0)):
            print(f"| {c} | {v:.1f} | {v / total * 100:.1f}% |")
        steps = json.loads((d / f"{wf}.steps.json").read_text(encoding="utf-8"))
        print("\n**Slowest steps:**\n")
        print("| Step | Category | n | p50 | p95 |\n|---|---|---:|---:|---:|")
        for st in steps[:12]:
            print(f"| {st['step']} | {st['category']} | {st['n']} | {mmss(st['p50_s'])} | {mmss(st['p95_s'])} |")
        print()
    print("### Individual runs\n")
    print("| Run | Commit | Wall-clock | Billable min | Cost (USD) | Overhead share |\n|---|---|---:|---:|---:|---:|")
    with (d / "runs.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            print(f"| {r['run_id']} | `{r['head_sha'][:8]}` | {mmss(r['wall_clock_s'])} | {r['billable_min']} | "
                  f"{float(r['cost_usd']):.3f} | {float(r['overhead_share']) * 100:.1f}% |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
