"""shardkit command-line interface.

shardkit durations --framework junit --junit 'target/*-reports/*.xml' --out durations/orders-unit.json
shardkit plan --framework junit --durations durations/orders-unit.json --units 'src/test/java/**/*Test.java' \
    --shards 4 --index 0 --style maven
shardkit compare --durations d.json --units '...' --framework junit --shards 4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import core


def _load(path: str | None) -> dict[str, float]:
    if not path or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_durations(a) -> int:
    files = core.expand(a.junit)
    if not files:
        print("no JUnit XML files matched", file=sys.stderr)
        return 1
    d = core.parse_junit(files, a.framework, root=a.root)
    if a.strip_prefix:
        pre = a.strip_prefix.rstrip("/") + "/"
        d = {k[len(pre):] if k.startswith(pre) else k: v for k, v in d.items()}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(d, indent=2, sort_keys=True), encoding="utf-8")
    print(f"{len(d)} units, {sum(d.values()):.1f}s total -> {a.out}")
    return 0


def _units(a) -> list[str]:
    units = core.discover(a.units, a.framework, strip_prefix=a.strip_prefix)
    if not units:
        raise SystemExit("no test units discovered")
    return units


def cmd_plan(a) -> int:
    units = _units(a)
    durations = _load(a.durations)
    plan = core.plan_lpt(durations, units, a.shards) if durations else core.plan_round_robin(units, a.shards)
    if not 0 <= a.index < a.shards:
        raise SystemExit("index must be in [0, shards)")
    print(core.render(plan[a.index], a.framework, a.style))
    if a.summary:
        info = core.imbalance(plan, durations)
        info["strategy"] = "lpt" if durations else "round-robin (no history)"
        print(json.dumps(info), file=sys.stderr)
    return 0


def cmd_compare(a) -> int:
    units = _units(a)
    durations = _load(a.durations)
    out = {
        "units": len(units),
        "shards": a.shards,
        "lpt": core.imbalance(core.plan_lpt(durations, units, a.shards), durations),
        "round_robin": core.imbalance(core.plan_round_robin(units, a.shards), durations),
    }
    print(json.dumps(out, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="shardkit", description="Duration-balanced test sharding")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("durations", help="aggregate JUnit XML into per-unit durations")
    d.add_argument("--framework", choices=core.FRAMEWORKS, required=True)
    d.add_argument("--junit", action="append", required=True, help="glob, repeatable")
    d.add_argument("--root", help="project root used to resolve pytest module paths")
    d.add_argument("--strip-prefix", help="strip this path prefix from unit names")
    d.add_argument("--out", required=True)
    d.set_defaults(func=cmd_durations)

    for name, func in (("plan", cmd_plan), ("compare", cmd_compare)):
        s = sub.add_parser(name)
        s.add_argument("--framework", choices=core.FRAMEWORKS, required=True)
        s.add_argument("--units", action="append", required=True, help="glob of test files, repeatable")
        s.add_argument("--strip-prefix", help="strip this path prefix from discovered file units")
        s.add_argument("--durations", help="durations JSON; missing file means round-robin")
        s.add_argument("--shards", type=int, required=True)
        if name == "plan":
            s.add_argument("--index", type=int, required=True)
            s.add_argument("--style", choices=["lines", "json", "maven", "args"], default="lines")
            s.add_argument("--summary", action="store_true", help="print shard loads to stderr")
        s.set_defaults(func=func)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
