"""Render the TIA fault-injection results (experiments/results/tia-faults-*.json) as Markdown.

Usage: python scripts/report_faults.py [results.json] > docs/phase-results/phase-4-tia-safety-tables.md
Numbers are computed from the results file only; nothing is typed by hand.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted((ROOT / "experiments/results").glob("tia-faults-*.json"))[-1]
    data = json.loads(path.read_text(encoding="utf-8"))
    s, rs = data["summary"], data["results"]
    print(f"Source: `{path.relative_to(ROOT).as_posix()}` (repo HEAD `{data['head'][:8]}`)\n")
    print("| App | Faults | Detected by full suite | Not detected by any test | Not viable | Hybrid recall | "
          "Static-only recall | Mean share of test units selected (hybrid) | (static-only) |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    tot = {"f": 0, "d": 0, "u": 0, "n": 0, "hd": 0, "sd": 0}
    for app, v in s.items():
        det = [r for r in rs if r["app"] == app and r.get("status") == "detected"]
        tot["f"] += v["faults"]; tot["d"] += v["detected_by_full"]; tot["u"] += v["undetected_by_suite"]
        tot["n"] += v["not_viable"]
        tot["hd"] += sum(r["hybrid"]["detected"] for r in det); tot["sd"] += sum(r["static"]["detected"] for r in det)
        print(f"| {app} | {v['faults']} | {v['detected_by_full']} | {v['undetected_by_suite']} | {v['not_viable']} | "
              f"{pct(v['hybrid_recall'])} | {pct(v['static_recall'])} | {pct(v['hybrid_mean_selected_share'])} | "
              f"{pct(v['static_mean_selected_share'])} |")
    print(f"| **all** | {tot['f']} | {tot['d']} | {tot['u']} | {tot['n']} | "
          f"{pct(tot['hd'] / tot['d'] if tot['d'] else None)} | {pct(tot['sd'] / tot['d'] if tot['d'] else None)} | | |")
    print()
    print("Selection share is over each app's unit and integration test units (e2e excluded: always run in full on web "
          "source changes). Units: Java test classes, Vitest files, pytest modules.\n")
    print("**Misses (fault detected by the full suite but not by the selection):** "
          + (", ".join(m for v in s.values() for m in v["hybrid_misses"]) or "none (hybrid)") + "; static-only: "
          + (", ".join(m for v in s.values() for m in v["static_misses"]) or "none") + ".\n")
    print("### Per-fault detail\n")
    print("| Fault | Operator | File:line | Status | Failing units | Hybrid selected | Static selected |")
    print("|---|---|---|---|---:|---:|---:|")
    for r in rs:
        if r.get("status") == "patch-failed":
            print(f"| {r['id']} | {r['operator']} | {r['file'].split('/')[-1]}:{r['line']} | patch failed | | | |")
            continue
        mark = lambda d: f"{d['n_selected']} {'✓' if d['detected'] else ('–' if r['status'] != 'detected' else '✗')}"
        print(f"| {r['id']} | {r['operator']} | `{r['file'].split('/')[-1]}:{r['line']}` | {r['status']} | "
              f"{len(r['failing_units'])} | {mark(r['hybrid'])} | {mark(r['static'])} |")
    print("\n✓ selection contains a failing unit · ✗ miss · – no test detects the fault at all")
    print("\n### Faults no test detects (test-suite gaps)\n")
    for r in rs:
        if r.get("status") == "undetected-by-suite":
            print(f"- `{r['id']}` `{r['file']}:{r['line']}` ({r['operator']}): `{r['before'][:70]}` → `{r['after'][:70]}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
