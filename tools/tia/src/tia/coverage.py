"""Dynamic coverage maps: source file -> test files that executed it.

Map file format (JSON):
    {"generated_at_epoch": 1761400000, "source": "...", "map": {"apps/x/src/a.py": ["apps/x/tests/test_a.py"]}}
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def _join(prefix: str, path: str) -> str:
    path = path.replace("\\", "/")
    return f"{prefix.rstrip('/')}/{path}" if prefix else path


def context_to_test_file(ctx: str) -> str | None:
    """coverage.py context 'tests/test_x.py::TestA::test_b|run' -> 'tests/test_x.py'."""
    if not ctx:
        return None
    node = ctx.split("|", 1)[0]
    file = node.split("::", 1)[0]
    return file.replace("\\", "/") if file.endswith(".py") else None


def from_coverage_py(data: dict, prefix: str = "") -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for src, info in data.get("files", {}).items():
        tests: set[str] = set()
        for ctxs in (info.get("contexts") or {}).values():
            for ctx in ctxs:
                t = context_to_test_file(ctx)
                if t:
                    tests.add(_join(prefix, t))
        if tests:
            out[_join(prefix, src)] = tests
    return out


def from_per_test_files(per_test: dict[str, list[str]], prefix: str = "") -> dict[str, set[str]]:
    """Invert {test_file: [covered source files]} into {source: {tests}}."""
    out: dict[str, set[str]] = {}
    for test, sources in per_test.items():
        for s in sources:
            out.setdefault(_join(prefix, s), set()).add(_join(prefix, test))
    return out


def write_map(path: Path, m: dict[str, set[str]], source: str, now: float | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at_epoch": int(now or time.time()), "source": source,
               "map": {k: sorted(v) for k, v in sorted(m.items())}}
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
