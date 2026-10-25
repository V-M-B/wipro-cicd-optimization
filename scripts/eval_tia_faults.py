"""TIA safety study: does the selected test subset catch every injected fault the full suite catches?

For each fault in experiments/faults/manifest.json, in an isolated git worktree:
  1. apply the fault patch,
  2. compute the tia selection for the changed file (hybrid = static + dynamic map, and static-only),
  3. run the app's FULL suite once and collect the failing test units from JUnit XML,
  4. the fault is "detected by full" if any test failed, and "detected by selection" if any failing unit is in
     the selection (equivalent to running the selected subset, without a second run).
Faults that break compilation/collection are reported as "not viable" (any test run would expose them).
Faults that no test detects are "undetected by the suite" and excluded from recall (no selection can do better).

Web end-to-end tests are not run here: tia always selects the full e2e suite on any web source change
(full_suite_on_source_change), so e2e cannot change the outcome.

Usage: python scripts/eval_tia_faults.py [--only orders-api-01,web-03] [--app web]
Writes experiments/results/tia-faults-<timestamp>.json and prints a summary table.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/tia/src"))
sys.path.insert(0, str(ROOT / "tools/shardkit/src"))

from shardkit.core import _pytest_unit  # noqa: E402
from tia.select import select  # noqa: E402

SCRATCH = Path(os.environ.get("TIA_EVAL_DIR", ROOT.parent / "tia-eval-worktree"))
JAVA_HOME = os.environ.get("JAVA_HOME_21", r"C:\Users\varun\tools\jdk-21.0.12.1+1")


def sh(args, cwd, env=None, timeout=1800):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout,
                          shell=isinstance(args, str))


def failing_units(app: str, wt: Path) -> tuple[set[str], int, bool]:
    """Run the full suite; return (failing units, tests run, viable)."""
    if app == "orders-api":
        d = wt / "apps/orders-api"
        shutil.rmtree(d / "target", ignore_errors=True)
        env = dict(os.environ, JAVA_HOME=JAVA_HOME)
        r = sh("bash ./mvnw -B -q verify -Dmaven.test.failure.ignore=true", d, env=env)
        xmls = list((d / "target/surefire-reports").glob("TEST-*.xml")) + \
            list((d / "target/failsafe-reports").glob("TEST-*.xml"))
        if not xmls:
            return set(), 0, False
        prefix = ""
    elif app == "web":
        d = wt / "apps/web"
        out = d / "reports/eval-junit.xml"
        out.unlink(missing_ok=True)
        sh("npx vitest run --reporter=junit --outputFile=reports/eval-junit.xml", d)
        if not out.exists():
            return set(), 0, False
        xmls = [out]
    else:
        d = wt / "apps/analytics"
        out = d / "reports/eval-junit.xml"
        out.unlink(missing_ok=True)
        py = str(ROOT / "apps/analytics/.venv/Scripts/python.exe")
        sh([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml=reports/eval-junit.xml"], d)
        if not out.exists():
            return set(), 0, False
        xmls = [out]
    failed: set[str] = set()
    total = 0
    collection_error = False
    for x in xmls:
        root = ET.parse(x).getroot()
        for suite in root.iter("testsuite"):
            for case in suite.findall("testcase"):
                total += 1
                bad = case.find("failure") is not None or case.find("error") is not None
                if not bad:
                    continue
                cls = case.get("classname") or suite.get("name") or ""
                if app == "orders-api":
                    failed.add(cls)
                elif app == "web":
                    failed.add((case.get("file") or suite.get("name") or cls).replace("\\", "/"))
                else:
                    if not case.get("name"):
                        collection_error = True
                    failed.add(_pytest_unit(cls, case.get("file"), wt / "apps/analytics"))
    if total == 0 or collection_error:
        return failed, total, False
    return failed, total, True


def selection_units(wt: Path, app: str, changed: str, static_only: bool) -> tuple[set[str], str]:
    config = tomllib.loads((wt / "tia.toml").read_text(encoding="utf-8"))
    res = select(wt, config, [changed], use_dynamic=not static_only)["apps"][app]
    units = {u for suite, us in res["suites"].items() if suite != "e2e" for u in us}
    return units, res["mode"]


def total_units(wt: Path, app: str) -> int:
    config = tomllib.loads((wt / "tia.toml").read_text(encoding="utf-8"))
    res = select(wt, config, [], force_full="count")["apps"][app]
    return sum(len(v) for s, v in res["suites"].items() if s != "e2e")


def ensure_worktree() -> Path:
    if not (SCRATCH / ".git").exists():
        sh(["git", "worktree", "add", "--detach", str(SCRATCH), "HEAD"], ROOT)
        # dependencies for web (node_modules is not shared between worktrees)
        sh("npm ci --no-audit --no-fund", SCRATCH / "apps/web", timeout=1800)
    return SCRATCH


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--app")
    a = ap.parse_args()
    faults = json.loads((ROOT / "experiments/faults/manifest.json").read_text(encoding="utf-8"))["faults"]
    if a.only:
        wanted = set(a.only.split(","))
        faults = [f for f in faults if f["id"] in wanted]
    if a.app:
        faults = [f for f in faults if f["app"] == a.app]
    wt = ensure_worktree()
    head = sh(["git", "rev-parse", "HEAD"], ROOT).stdout.strip()
    sh(["git", "checkout", "-q", "--detach", head], wt)
    results = []
    for f in faults:
        sh(["git", "checkout", "-q", "--", "."], wt)
        t0 = time.time()
        r = sh(["git", "apply", str(ROOT / f["patch"])], wt)
        if r.returncode != 0:
            results.append({**f, "status": "patch-failed", "error": r.stderr[-300:]})
            print(f"{f['id']}: patch failed")
            continue
        hyb, hyb_mode = selection_units(wt, f["app"], f["file"], static_only=False)
        sta, sta_mode = selection_units(wt, f["app"], f["file"], static_only=True)
        failed, n_tests, viable = failing_units(f["app"], wt)
        sh(["git", "checkout", "-q", "--", "."], wt)
        rec = {**f, "tests_run": n_tests, "viable": viable, "failing_units": sorted(failed),
               "detected_full": bool(failed) and viable,
               "hybrid": {"mode": hyb_mode, "n_selected": len(hyb), "detected": bool(failed & hyb)},
               "static": {"mode": sta_mode, "n_selected": len(sta), "detected": bool(failed & sta)},
               "seconds": round(time.time() - t0, 1)}
        rec["status"] = ("not-viable" if not viable else "undetected-by-suite" if not failed else "detected")
        results.append(rec)
        print(f"{f['id']:15s} {rec['status']:20s} fail={len(failed):2d} hybrid={len(hyb):3d}"
              f"{'+' if rec['hybrid']['detected'] else '-'} static={len(sta):3d}{'+' if rec['static']['detected'] else '-'}"
              f"  {rec['seconds']}s", flush=True)
    totals = {app: total_units(wt, app) for app in ("orders-api", "web", "analytics")}
    summary = {}
    for app in sorted({r["app"] for r in results}):
        rs = [r for r in results if r["app"] == app and r.get("status") == "detected"]
        summary[app] = {
            "faults": sum(1 for r in results if r["app"] == app),
            "detected_by_full": len(rs),
            "not_viable": sum(1 for r in results if r["app"] == app and r.get("status") == "not-viable"),
            "undetected_by_suite": sum(1 for r in results if r["app"] == app and r.get("status") == "undetected-by-suite"),
            "hybrid_recall": (sum(r["hybrid"]["detected"] for r in rs) / len(rs)) if rs else None,
            "static_recall": (sum(r["static"]["detected"] for r in rs) / len(rs)) if rs else None,
            "hybrid_mean_selected_share": (sum(r["hybrid"]["n_selected"] for r in rs) / len(rs) / totals[app]) if rs else None,
            "static_mean_selected_share": (sum(r["static"]["n_selected"] for r in rs) / len(rs) / totals[app]) if rs else None,
            "total_units": totals[app],
            "hybrid_misses": [r["id"] for r in rs if not r["hybrid"]["detected"]],
            "static_misses": [r["id"] for r in rs if not r["static"]["detected"]],
        }
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = ROOT / f"experiments/results/tia-faults-{stamp}.json"
    out.write_text(json.dumps({"head": head, "summary": summary, "results": results}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
