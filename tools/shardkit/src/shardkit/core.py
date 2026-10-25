"""Duration-balanced test sharding.

Units are the granularity a framework can select: a Java test class (FQN), a Vitest/Playwright spec file,
or a pytest module path. Durations come from JUnit XML produced by previous runs.
"""
from __future__ import annotations

import glob
import heapq
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path, PurePosixPath

FRAMEWORKS = ("junit", "vitest", "playwright", "pytest")


def _posix(p: str) -> str:
    return str(PurePosixPath(Path(p).as_posix()))


def _pytest_unit(classname: str, file_attr: str | None, root: Path | None) -> str:
    if file_attr:
        return _posix(file_attr)
    parts = classname.split(".")
    if root is not None:
        # longest dotted prefix that exists as a module file wins
        for i in range(len(parts), 0, -1):
            cand = "/".join(parts[:i]) + ".py"
            if (root / cand).exists():
                return cand
    # no root (or nothing found): drop trailing CamelCase class names
    while len(parts) > 1 and parts[-1][:1].isupper():
        parts.pop()
    return "/".join(parts) + ".py"


def parse_junit(paths: list[str], framework: str, root: str | None = None) -> dict[str, float]:
    """Aggregate testcase durations (seconds) per selectable unit."""
    if framework not in FRAMEWORKS:
        raise ValueError(f"framework must be one of {FRAMEWORKS}")
    rootp = Path(root) if root else None
    totals: dict[str, float] = defaultdict(float)
    for path in paths:
        tree = ET.parse(path)
        for suite in tree.iter("testsuite"):
            suite_name = suite.get("name") or ""
            suite_file = suite.get("file")
            for case in suite.findall("testcase"):
                t = float(case.get("time") or 0)
                cls = case.get("classname") or suite_name
                if framework == "junit":
                    unit = cls
                elif framework in ("vitest", "playwright"):
                    unit = _posix(case.get("file") or suite_file or suite_name or cls)
                else:
                    unit = _pytest_unit(cls, case.get("file"), rootp)
                totals[unit] += t
    return {k: round(v, 3) for k, v in sorted(totals.items())}


def expand(patterns: list[str]) -> list[str]:
    out: list[str] = []
    for p in patterns:
        matches = sorted(glob.glob(p, recursive=True))
        out.extend(matches if matches else [])
    return sorted(set(out))


def java_unit_from_path(path: str, source_root: str = "src/test/java") -> str:
    p = _posix(path)
    marker = source_root.rstrip("/") + "/"
    if marker in p:
        p = p.split(marker, 1)[1]
    return p.removesuffix(".java").replace("/", ".")


def discover(patterns: list[str], framework: str, strip_prefix: str | None = None) -> list[str]:
    files = expand(patterns)
    if framework == "junit":
        return sorted(java_unit_from_path(f) for f in files)
    units = [_posix(f) for f in files]
    if strip_prefix:
        pre = _posix(strip_prefix).rstrip("/") + "/"
        units = [u[len(pre):] if u.startswith(pre) else u for u in units]
    return sorted(units)


def _estimate(durations: dict[str, float], units: list[str]) -> dict[str, float]:
    known = sorted(v for k, v in durations.items() if k in set(units))
    fallback = known[len(known) // 2] if known else 1.0
    return {u: durations.get(u, fallback) for u in units}


def plan_lpt(durations: dict[str, float], units: list[str], shards: int) -> list[list[str]]:
    """Longest-processing-time-first greedy bin packing. Deterministic."""
    if shards < 1:
        raise ValueError("shards must be >= 1")
    est = _estimate(durations, units)
    heap = [(0.0, i) for i in range(shards)]
    out: list[list[str]] = [[] for _ in range(shards)]
    for unit in sorted(units, key=lambda u: (-est[u], u)):
        load, i = heapq.heappop(heap)
        out[i].append(unit)
        heapq.heappush(heap, (load + est[unit], i))
    return [sorted(s) for s in out]


def plan_round_robin(units: list[str], shards: int) -> list[list[str]]:
    out: list[list[str]] = [[] for _ in range(shards)]
    for i, u in enumerate(sorted(units)):
        out[i % shards].append(u)
    return out


def loads(plan: list[list[str]], durations: dict[str, float]) -> list[float]:
    all_units = [u for s in plan for u in s]
    est = _estimate(durations, all_units)
    return [round(sum(est[u] for u in s), 3) for s in plan]


def imbalance(plan: list[list[str]], durations: dict[str, float]) -> dict:
    ls = loads(plan, durations)
    return {"loads_s": ls, "max_s": max(ls), "min_s": min(ls), "spread_s": round(max(ls) - min(ls), 3),
            "ideal_s": round(sum(ls) / len(ls), 3)}


def render(units: list[str], framework: str, style: str) -> str:
    """Render the unit list for a test runner command line."""
    if style == "lines":
        return "\n".join(units)
    if style == "json":
        return json.dumps(units)
    if style == "maven":
        return ",".join(units)
    if style == "args":
        return " ".join(units)
    raise ValueError(f"unknown style {style}")
