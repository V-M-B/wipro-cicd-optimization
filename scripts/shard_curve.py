"""Shard-count experiment for ci-parallel.yml: dispatch N-shard runs one at a time and summarize.

The workflow's `shards` input sets the matrix size of every sharded suite. Each dispatch is waited on before the
next, so runs do not compete for the 20 concurrent-job limit. The run id of each dispatch is recorded next to its
shard count (the runs API does not expose dispatch inputs).

Usage:
  python scripts/shard_curve.py run --shards 1 2 4 8 --repeats 3      # dispatch and wait (hours)
  python scripts/shard_curve.py summarize                              # after `cipro fetch`, writes shard-curve-*.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "experiments/results/shard-curve-dispatches.jsonl"
REPO = "V-M-B/wipro-cicd-optimization"


def gh(*args: str) -> str:
    for attempt in range(10):
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
        time.sleep(60)
    raise SystemExit(f"gh {' '.join(args)} failed: {r.stderr}")


def latest_dispatch_id() -> int | None:
    out = gh("api", f"repos/{REPO}/actions/workflows/ci-parallel.yml/runs?event=workflow_dispatch&per_page=1")
    runs = json.loads(out)["workflow_runs"]
    return runs[0]["id"] if runs else None


def cmd_run(a) -> int:
    for rep in range(a.repeats):
        for n in a.shards:
            before = latest_dispatch_id()
            gh("workflow", "run", "ci-parallel.yml", "--ref", "main", "-f", f"shards={n}")
            run_id = None
            for _ in range(60):
                time.sleep(10)
                rid = latest_dispatch_id()
                if rid and rid != before:
                    run_id = rid
                    break
            if run_id is None:
                raise SystemExit("dispatched run did not appear")
            while True:
                st = json.loads(gh("api", f"repos/{REPO}/actions/runs/{run_id}"))
                if st["status"] == "completed":
                    break
                time.sleep(45)
            rec = {"shards": n, "repeat": rep, "run_id": run_id, "conclusion": st["conclusion"]}
            print(json.dumps(rec), flush=True)
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
    return 0


def cmd_summarize(a) -> int:
    sys.path.insert(0, str(ROOT / "tools/cipro/src"))
    from cipro import store
    from cipro.metrics import run_metrics

    con = store.connect(ROOT / "experiments/results/cipro.sqlite")
    recs = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    by: dict[int, list] = {}
    for r in recs:
        if r["conclusion"] != "success":
            continue
        if con.execute("SELECT 1 FROM runs WHERE id=?", (r["run_id"],)).fetchone() is None:
            print(f"run {r['run_id']} not fetched yet; run cipro fetch first", file=sys.stderr)
            continue
        by.setdefault(r["shards"], []).append(run_metrics(con, r["run_id"]))
    points = []
    for n in sorted(by):
        ms = by[n]
        points.append({"shards": n, "n": len(ms),
                       "wall_p50_s": statistics.median(m.wall_clock_s for m in ms),
                       "billable_p50": statistics.median(m.billable_min for m in ms),
                       "job_seconds_p50": statistics.median(m.job_seconds for m in ms),
                       "run_ids": [m.id for m in ms]})
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = ROOT / f"experiments/results/shard-curve-{stamp}.json"
    out.write_text(json.dumps({"points": points}, indent=2), encoding="utf-8")
    print("| Shards | Runs | Wall-clock p50 | Billable min p50 | Job-seconds p50 |\n|---:|---:|---:|---:|---:|")
    for p in points:
        print(f"| {p['shards']} | {p['n']} | {p['wall_p50_s']:.0f} s | {p['billable_p50']:.0f} | {p['job_seconds_p50']:.0f} |")
    print(f"\nwrote {out.relative_to(ROOT).as_posix()}")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--shards", type=int, nargs="+", default=[1, 2, 4, 8])
    r.add_argument("--repeats", type=int, default=3)
    r.set_defaults(func=cmd_run)
    s = sub.add_parser("summarize")
    s.set_defaults(func=cmd_summarize)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
