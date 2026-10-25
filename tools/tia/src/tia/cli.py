"""tia command-line interface.

tia select --config tia.toml --base origin/main --head HEAD --out selection.json [--static-only]
tia show   --selection selection.json --app orders-api --suite unit --style maven
tia coverage-python --coverage-json coverage.json --out experiments/coverage/analytics.json --prefix apps/analytics
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import tomllib
from pathlib import Path

from . import coverage as cov
from .select import changed_files, normalize, select


def cmd_select(a) -> int:
    repo = Path(a.repo).resolve()
    config = tomllib.loads(Path(a.config).read_text(encoding="utf-8"))
    if a.force_full:
        changed = []
    elif a.changed:
        changed = normalize(Path(a.changed).read_text(encoding="utf-8").split())
    else:
        changed = changed_files(repo, a.base, a.head)
    t0 = time.perf_counter()
    result = select(repo, config, changed, use_dynamic=not a.static_only, force_full=a.force_full)
    result["selection_seconds"] = round(time.perf_counter() - t0, 3)
    result["base"], result["head"], result["static_only"] = a.base, a.head, a.static_only
    text = json.dumps(result, indent=2)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
    for name, d in result["apps"].items():
        sel = ", ".join(f"{s}={n}/{d['total_units'].get(s, 0)}" for s, n in d["selected_units"].items())
        print(f"{name:12s} {d['mode']:6s} {sel}  | {'; '.join(d['reasons'])}", file=sys.stderr)
    if not a.out:
        print(text)
    return 0


def cmd_show(a) -> int:
    sel = json.loads(Path(a.selection).read_text(encoding="utf-8"))
    d = sel["apps"][a.app]
    if a.field == "mode":
        print(d["mode"])
        return 0
    units = d["suites"].get(a.suite, [])
    sep = {"maven": ",", "args": " ", "lines": "\n"}[a.style]
    print(sep.join(units))
    return 0


def cmd_coverage_python(a) -> int:
    data = json.loads(Path(a.coverage_json).read_text(encoding="utf-8"))
    m = cov.from_coverage_py(data, prefix=a.prefix)
    cov.write_map(Path(a.out), m, source="coverage.py dynamic contexts")
    print(f"{len(m)} source files mapped -> {a.out}")
    return 0


def cmd_coverage_istanbul(a) -> int:
    m = cov.from_istanbul_dir(Path(a.dir), prefix=a.prefix)
    cov.write_map(Path(a.out), m, source="istanbul per-test-file coverage")
    print(f"{len(m)} source files mapped -> {a.out}")
    return 0


def cmd_coverage_jacoco(a) -> int:
    m = cov.from_jacoco_dir(Path(a.dir), prefix=a.prefix)
    cov.write_map(Path(a.out), m, source="jacoco per-test-class coverage")
    print(f"{len(m)} source files mapped -> {a.out}")
    return 0


def cmd_coverage_merge(a) -> int:
    merged: dict[str, set[str]] = {}
    for p in a.inputs:
        part = json.loads(Path(p).read_text(encoding="utf-8"))["map"]
        for src, tests in part.items():
            merged.setdefault(src, set()).update(tests)
    cov.write_map(Path(a.out), merged, source=f"merged from {len(a.inputs)} maps")
    print(f"{len(merged)} source files mapped -> {a.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tia", description="Test impact analysis")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("select")
    s.add_argument("--config", default="tia.toml")
    s.add_argument("--repo", default=".")
    s.add_argument("--base", default="origin/main")
    s.add_argument("--head", default="HEAD")
    s.add_argument("--changed", help="file with changed paths (one per line) instead of git diff")
    s.add_argument("--static-only", action="store_true")
    s.add_argument("--force-full", metavar="REASON", help="select every suite of every app (safety net runs)")
    s.add_argument("--out")
    s.set_defaults(func=cmd_select)

    sh = sub.add_parser("show")
    sh.add_argument("--selection", required=True)
    sh.add_argument("--app", required=True)
    sh.add_argument("--suite", default="unit")
    sh.add_argument("--field", choices=["units", "mode"], default="units")
    sh.add_argument("--style", choices=["maven", "args", "lines"], default="lines")
    sh.set_defaults(func=cmd_show)

    c = sub.add_parser("coverage-python", help="build a map from `coverage json --show-contexts`")
    c.add_argument("--coverage-json", required=True)
    c.add_argument("--prefix", default="", help="repo-relative app root to prepend, e.g. apps/analytics")
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_coverage_python)

    ci = sub.add_parser("coverage-istanbul", help="build a map from per-test-file istanbul JSON")
    ci.add_argument("--dir", required=True)
    ci.add_argument("--prefix", required=True, help="repo-relative app root, e.g. apps/web")
    ci.add_argument("--out", required=True)
    ci.set_defaults(func=cmd_coverage_istanbul)

    cj = sub.add_parser("coverage-jacoco", help="build a map from per-test-class JaCoCo XML reports")
    cj.add_argument("--dir", required=True)
    cj.add_argument("--prefix", required=True, help="repo-relative app root, e.g. apps/orders-api")
    cj.add_argument("--out", required=True)
    cj.set_defaults(func=cmd_coverage_jacoco)

    mg = sub.add_parser("coverage-merge", help="merge several coverage maps")
    mg.add_argument("inputs", nargs="+")
    mg.add_argument("--out", required=True)
    mg.set_defaults(func=cmd_coverage_merge)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
