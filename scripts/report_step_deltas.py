"""Per-step median durations for two workflows on the same commits (attribution of a stage's saving to steps).

Steps are matched by name after normalising known renames (the cache stage splits the Playwright step and adds
cache-restore steps). Usage:
    python scripts/report_step_deltas.py --a ci-baseline.yml --b ci-cache.yml --branch-glob 'exp/a/*'
Writes experiments/results/step-deltas-<a>-vs-<b>-<timestamp>.json and prints Markdown.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/cipro/src"))
from cipro import store  # noqa: E402
from cipro.metrics import seconds, workflow_runs  # noqa: E402

GROUPS = {
    "Toolchain setup (Java/Node/Python)": ["Set up Java 21", "Set up Node 20", "Set up Python 3.12",
                                           "Set up Java 21 (with Maven cache)", "Set up Node 20 (with npm cache)",
                                           "Set up Python 3.12 (with pip cache)"],
    "orders-api build and tests (Maven dependencies)": ["orders-api - build and test"],
    "web npm ci": ["web - install"],
    "Playwright browsers and system packages": ["web - install Playwright browsers", "web - resolve Playwright version",
                                                "web - restore Playwright browsers cache",
                                                "web - install Playwright system dependencies"],
    "analytics pip install": ["analytics - install"],
    # build and push are one group: the cache stage pushes inside its build-push steps
    "Docker image build, push and registry login": ["Build images", "Push images", "Log in to GHCR",
                                                    "Set up Docker Buildx", "Build and push image orders-api",
                                                    "Build and push image web", "Build and push image analytics",
                                                    "Image tag prefix"],
    "Post-job cache save and cleanup": ["Post Set up Java 21 (with Maven cache)", "Post Set up Node 20 (with npm cache)",
                                        "Post Set up Python 3.12 (with pip cache)", "Post web - restore Playwright browsers cache",
                                        "Post Set up Docker Buildx", "Post Build and push image orders-api",
                                        "Post Build and push image web", "Post Build and push image analytics",
                                        "Post Set up Java 21", "Post Set up Node 20", "Post Set up Python 3.12",
                                        "Post Log in to GHCR"],
}


def per_run_groups(con, run_id: int) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    rows = con.execute("SELECT s.name, s.started_at, s.completed_at FROM steps s JOIN jobs j ON j.id=s.job_id "
                       "WHERE j.run_id=?", (run_id,)).fetchall()
    for name, a, b in rows:
        d = seconds(a, b) or 0
        for g, names in GROUPS.items():
            if name in names:
                out[g] += d
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--branch-glob", required=True)
    ap.add_argument("--db", default=str(ROOT / "experiments/results/cipro.sqlite"))
    args = ap.parse_args()
    con = store.connect(args.db)
    A = {r.head_sha: r for r in workflow_runs(con, args.a, branch_glob=args.branch_glob)}
    B = {r.head_sha: r for r in workflow_runs(con, args.b, branch_glob=args.branch_glob)}
    shas = sorted(set(A) & set(B))
    res = {}
    for g in GROUPS:
        a = [per_run_groups(con, A[s].id).get(g, 0.0) for s in shas]
        b = [per_run_groups(con, B[s].id).get(g, 0.0) for s in shas]
        diffs = [y - x for x, y in zip(a, b)]
        res[g] = {"a_p50_s": statistics.median(a), "b_p50_s": statistics.median(b),
                  "paired_diff_p50_s": statistics.median(diffs), "n": len(shas)}
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = ROOT / f"experiments/results/step-deltas-{args.a[:-4]}-vs-{args.b[:-4]}-{stamp}.json"
    out.write_text(json.dumps({"a": args.a, "b": args.b, "branch_glob": args.branch_glob, "groups": res}, indent=2),
                   encoding="utf-8")
    print(f"Median per-run seconds on {len(shas)} paired commits (`{args.branch_glob}`). "
          f"Source: `{out.relative_to(ROOT).as_posix()}`\n")
    print(f"| Step group | `{args.a}` p50 (s) | `{args.b}` p50 (s) | Median paired difference (s) |")
    print("|---|---:|---:|---:|")
    for g, v in res.items():
        print(f"| {g} | {v['a_p50_s']:.0f} | {v['b_p50_s']:.0f} | {v['paired_diff_p50_s']:+.0f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
