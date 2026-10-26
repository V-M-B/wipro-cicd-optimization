"""Count slow Playwright browser/system-dependency install steps per workflow (Phase 0 correction table).

Usage: python scripts/report_playwright_steps.py [--db experiments/results/cipro.sqlite] [--threshold 300]
Writes experiments/results/playwright-install-steps-<timestamp>.json and prints a Markdown table.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def seconds(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return (f(b) - f(a)).total_seconds()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "experiments/results/cipro.sqlite"))
    ap.add_argument("--threshold", type=float, default=300)
    a = ap.parse_args()
    con = sqlite3.connect(a.db)
    rows = con.execute(
        """select r.workflow, s.name, s.started_at, s.completed_at from steps s
           join jobs j on j.id = s.job_id join runs r on r.id = j.run_id
           where s.conclusion = 'success' and (s.name like '%install Playwright browsers%'
             or s.name like '%Playwright system dependencies%' or s.name like 'Install Playwright browser%')"""
    ).fetchall()
    agg: dict[tuple[str, str], dict] = defaultdict(lambda: {"n": 0, "slow": 0, "slow_seconds": []})
    for wf, name, s, e in rows:
        d = seconds(s, e) or 0
        if d < 1:  # skipped by a cache hit
            continue
        k = (wf, name)
        agg[k]["n"] += 1
        if d > a.threshold:
            agg[k]["slow"] += 1
            agg[k]["slow_seconds"].append(round(d))
    out = [{"workflow": wf, "step": name, **v} for (wf, name), v in sorted(agg.items())]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = ROOT / f"experiments/results/playwright-install-steps-{stamp}.json"
    path.write_text(json.dumps({"threshold_s": a.threshold, "rows": out}, indent=2), encoding="utf-8")
    print(f"| Workflow | Step | Successful steps | > {a.threshold:.0f} s |\n|---|---|---:|---:|")
    for r in out:
        print(f"| {r['workflow']} | {r['step']} | {r['n']} | {r['slow']} {sorted(r['slow_seconds'])} |")
    print(f"\nwrote {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
