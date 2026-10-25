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


def _after(path: str, marker: str) -> str | None:
    p = path.replace("\\", "/")
    m = "/" + marker.strip("/") + "/"
    i = p.rfind(m)
    return p[i + len(m):] if i >= 0 else None


def from_istanbul_dir(directory: Path, prefix: str) -> dict[str, set[str]]:
    """Directory of pairs <n>.json (istanbul coverage-final.json of ONE test file) and <n>.test (that test
    file's path relative to the app root). Sources are made repo-relative by locating `prefix` in their path."""
    per_test: dict[str, list[str]] = {}
    for test_file in sorted(directory.glob("*.test")):
        test = test_file.read_text(encoding="utf-8").strip()
        cov_path = test_file.with_suffix(".json")
        if not cov_path.exists():
            continue
        data = json.loads(cov_path.read_text(encoding="utf-8"))
        covered = []
        for src, info in data.items():
            if any(v > 0 for v in (info.get("s") or {}).values()):
                rel = _after(info.get("path", src), prefix)
                if rel:
                    covered.append(rel)
        per_test[test] = covered
    return from_per_test_files(per_test, prefix=prefix)


def from_jacoco_dir(directory: Path, prefix: str, source_root: str = "src/main/java",
                    test_root: str = "src/test/java") -> dict[str, set[str]]:
    """Directory of <fully.qualified.TestClass>.xml JaCoCo XML reports, one per test class."""
    import xml.etree.ElementTree as ET

    per_test: dict[str, list[str]] = {}
    for report in sorted(directory.glob("*.xml")):
        fqn = report.stem
        test = f"{test_root}/{fqn.replace('.', '/')}.java"
        root = ET.parse(report).getroot()
        covered = []
        for pkg in root.iter("package"):
            for sf in pkg.findall("sourcefile"):
                for c in sf.findall("counter"):
                    if c.get("type") == "LINE" and int(c.get("covered", "0")) > 0:
                        covered.append(f"{source_root}/{pkg.get('name')}/{sf.get('name')}")
                        break
        per_test[test] = covered
    return from_per_test_files(per_test, prefix=prefix)
