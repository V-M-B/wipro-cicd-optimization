"""Tests executed and wall-clock by change category: baseline vs a test-selecting stage, from cipro data.

Test counts come from the job logs parsed by `cipro logs` (Maven, Vitest, Playwright and pytest summary lines).
Commits are paired by head_sha; the category is taken from the replay branch name exp/<round>/<NN>-<category>.

Usage: python scripts/report_tia_ci.py --round a --b ci-optimized.yml
Writes experiments/results/tia-ci-<round>-<timestamp>.json and prints Markdown.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/cipro/src"))
from cipro import store  # noqa: E402
from cipro.metrics import workflow_runs  # noqa: E402


def tests_in_run(con: sqlite3.Connection, run_id: int) -> tuple[float | None, int, int]:
    """(total tests, jobs with parsed logs, executed jobs)."""
    jobs = con.execute("SELECT id FROM jobs WHERE run_id=? AND conclusion='success'", (run_id,)).fetchall()
    ids = [j[0] for j in jobs]
    if not ids:
        return None, 0, 0
    q = ",".join("?" * len(ids))
    fetched = con.execute(f"SELECT COUNT(*) FROM logs_fetched WHERE job_id IN ({q})", ids).fetchone()[0]
    total = con.execute(
        f"SELECT SUM(value) FROM log_events WHERE kind LIKE 'tests_%' AND job_id IN ({q})", ids).fetchone()[0]
    return total, fetched, len(ids)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--a", default="ci-baseline.yml")
    ap.add_argument("--b", required=True)
    ap.add_argument("--db", default=str(ROOT / "experiments/results/cipro.sqlite"))
    args = ap.parse_args()
    con = store.connect(args.db)
    glob = f"exp/{args.round}/*"
    A = {r.head_sha: r for r in workflow_runs(con, args.a, branch_glob=glob)}
    B = {r.head_sha: r for r in workflow_runs(con, args.b, branch_glob=glob)}
    rows = []
    for sha in sorted(set(A) & set(B)):
        a, b = A[sha], B[sha]
        m = re.match(rf"exp/{args.round}/(\d+)-(.+)", a.head_branch)
        ta, fa, na = tests_in_run(con, a.id)
        tb, fb, nb = tests_in_run(con, b.id)
        rows.append({
            "id": int(m.group(1)), "category": m.group(2), "sha": sha,
            "a_wall_s": a.wall_clock_s, "b_wall_s": b.wall_clock_s,
            "a_tests": ta, "b_tests": tb, "a_logs_complete": fa == na, "b_logs_complete": fb == nb,
            "b_jobs": nb, "b_billable_min": b.billable_min, "a_billable_min": a.billable_min,
        })
    rows.sort(key=lambda r: r["id"])
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    def med(xs):
        xs = [x for x in xs if x is not None]
        return statistics.median(xs) if xs else None

    summary = {}
    for cat, rs in sorted(by_cat.items()):
        complete = [r for r in rs if r["a_logs_complete"] and r["b_logs_complete"] and r["a_tests"]]
        share = [(r["b_tests"] or 0) / r["a_tests"] for r in complete]
        summary[cat] = {
            "commits": len(rs), "commits_with_complete_logs": len(complete),
            "tests_executed_share_median": med(share),
            "wall_a_p50_s": med([r["a_wall_s"] for r in rs]), "wall_b_p50_s": med([r["b_wall_s"] for r in rs]),
            "jobs_b_median": med([r["b_jobs"] for r in rs]),
            "billable_a_median": med([r["a_billable_min"] for r in rs]),
            "billable_b_median": med([r["b_billable_min"] for r in rs]),
        }
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = ROOT / f"experiments/results/tia-ci-{args.round}-{stamp}.json"
    out.write_text(json.dumps({"a": args.a, "b": args.b, "round": args.round, "summary": summary, "rows": rows},
                              indent=2), encoding="utf-8")

    def pct(x):
        return "n/a" if x is None else f"{x * 100:.0f}%"

    def mmss(s):
        return "n/a" if s is None else f"{int(s // 60)}m {int(round(s % 60)):02d}s"

    print(f"Paired by commit, round {args.round}: `{args.a}` vs `{args.b}`. Source: `{out.relative_to(ROOT).as_posix()}`\n")
    print("| Category | Commits | Tests executed (median share of baseline) | Wall p50 baseline | Wall p50 stage | "
          "Jobs (median) | Billable min p50 baseline → stage |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for cat, s in summary.items():
        print(f"| {cat} | {s['commits']} ({s['commits_with_complete_logs']} with logs) | "
              f"{pct(s['tests_executed_share_median'])} | {mmss(s['wall_a_p50_s'])} | {mmss(s['wall_b_p50_s'])} | "
              f"{s['jobs_b_median']:.0f} | {s['billable_a_median']:.0f} → {s['billable_b_median']:.0f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
