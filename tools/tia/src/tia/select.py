"""Test selection: changed files -> per-app decision (none | subset | full) with reasons.

Configuration (tia.toml at the repo root):

    [settings]
    coverage_max_age_days = 7
    always_full_globs = [".github/workflows/**"]     # any match -> full suite for every app

    [[app]]
    name = "orders-api"
    language = "java"                  # java | ts | python
    root = "apps/orders-api"
    sources = ["src/main/java/**/*.java"]
    suites = { unit = ["src/test/java/**/*Test.java"], integration = ["src/test/java/**/*IT.java"] }
    full_globs = ["pom.xml", "Dockerfile", ".mvn/**", "src/main/resources/**"]
    ignore_globs = ["README.md", "**/*.md"]
    smoke = { unit = ["src/test/java/com/retailops/orders/SmokeTest.java"] }
    unit_style = "java-class"          # how units are reported: java-class | path
    coverage_map = "experiments/coverage/orders-api.json"
"""
from __future__ import annotations

import fnmatch
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import graph as g


def match(path: str, patterns: list[str]) -> bool:
    return any(_glob_match(path, p) for p in patterns)


def _glob_match(path: str, pattern: str) -> bool:
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if "**/" in pattern:
        # allow ** to match zero directories
        return fnmatch.fnmatchcase(path, pattern.replace("**/", "", 1))
    return False


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", f"{base}...{head}"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout
    return sorted(line.strip() for line in out.splitlines() if line.strip())


@dataclass
class AppDecision:
    app: str
    mode: str = "none"                             # none | subset | full
    suites: dict[str, list[str]] = field(default_factory=dict)   # suite -> selected units
    reasons: list[str] = field(default_factory=list)
    total_units: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"app": self.app, "mode": self.mode, "suites": self.suites, "reasons": self.reasons,
                "total_units": self.total_units,
                "selected_units": {k: len(v) for k, v in self.suites.items()}}


class App:
    def __init__(self, cfg: dict, repo: Path):
        self.cfg = cfg
        self.repo = repo
        self.name = cfg["name"]
        self.root = cfg["root"].rstrip("/")
        self.language = cfg["language"]

    def _files(self, patterns: list[str]) -> list[Path]:
        base = self.repo / self.root
        out: set[Path] = set()
        for p in patterns:
            out |= {f for f in base.glob(p) if f.is_file()}
        return sorted(out)

    def owns(self, path: str) -> bool:
        return path.startswith(self.root + "/")

    def local(self, path: str) -> str:
        return path[len(self.root) + 1:] if self.owns(path) else path

    def suite_files(self) -> dict[str, list[str]]:
        return {s: [g.rel(f, self.repo) for f in self._files(globs)] for s, globs in self.cfg["suites"].items()}

    def unit(self, test_path: str) -> str:
        if self.cfg.get("unit_style") == "java-class":
            from_root = self.local(test_path)
            marker = "src/test/java/"
            if marker in from_root:
                from_root = from_root.split(marker, 1)[1]
            return from_root.removesuffix(".java").replace("/", ".")
        return self.local(test_path)

    def build_graph(self) -> dict[str, set[str]]:
        test_globs = [p for globs in self.cfg["suites"].values() for p in globs]
        extra = self.cfg.get("support", [])
        files = self._files(self.cfg["sources"] + test_globs + extra)
        if self.language == "java":
            return g.java_graph(files, self.repo)
        if self.language == "ts":
            aliases = {k: self.repo / self.root / v for k, v in self.cfg.get("aliases", {}).items()}
            return g.ts_graph(files, self.repo, aliases)
        if self.language == "python":
            roots = [self.repo / self.root / r for r in self.cfg.get("python_roots", ["."])]
            return g.python_graph(files, self.repo, roots)
        raise ValueError(f"unknown language {self.language}")

    def coverage_map(self, max_age_days: float, now: float | None = None) -> tuple[dict[str, set[str]] | None, str]:
        path = self.cfg.get("coverage_map")
        if not path:
            return None, "no coverage map configured"
        p = self.repo / path
        if not p.exists():
            return None, f"coverage map {path} missing"
        data = json.loads(p.read_text(encoding="utf-8"))
        generated = data.get("generated_at_epoch", 0)
        age_days = ((now or time.time()) - generated) / 86400
        if age_days > max_age_days:
            return None, f"coverage map {path} is {age_days:.1f} days old (> {max_age_days})"
        # stored as source (repo-relative) -> list of test files (repo-relative)
        return {k: set(v) for k, v in data["map"].items()}, f"coverage map {path} ({age_days:.1f} days old)"


def decide(app: App, changed: list[str], settings: dict, now: float | None = None,
           use_dynamic: bool = True, force_full: str | None = None) -> AppDecision:
    d = AppDecision(app.name)
    suites = app.suite_files()
    d.total_units = {s: len(v) for s, v in suites.items()}
    all_tests = {t: s for s, ts in suites.items() for t in ts}

    def full(reason: str) -> AppDecision:
        d.mode = "full"
        d.reasons.append(reason)
        d.suites = {s: sorted(app.unit(t) for t in ts) for s, ts in suites.items()}
        return d

    if force_full:
        return full(f"forced: {force_full}")

    always = settings.get("always_full_globs", [])
    for f in changed:
        if match(f, always):
            return full(f"global trigger: {f}")

    mine = [f for f in changed if app.owns(f)]
    ignore = app.cfg.get("ignore_globs", [])
    relevant = [f for f in mine if not match(app.local(f), ignore)]
    if not relevant:
        d.reasons.append("no relevant changes" if not mine else f"only ignored files changed ({len(mine)})")
        return d

    for f in relevant:
        if match(app.local(f), app.cfg.get("full_globs", [])):
            return full(f"full trigger: {f}")

    static = g.reverse_closure(app.build_graph(), list(all_tests))
    dynamic, dyn_note = (app.coverage_map(settings.get("coverage_max_age_days", 7), now)
                         if use_dynamic else (None, "dynamic map disabled"))
    d.reasons.append(f"static graph over {len(all_tests)} test files; {dyn_note}")

    selected: set[str] = set()
    for f in relevant:
        if f in all_tests:
            selected.add(f)
            continue
        hits = set(static.get(f, set()))
        if dynamic is not None:
            hits |= dynamic.get(f, set()) & set(all_tests)
        if not hits:
            known = f in static or (dynamic is not None and f in dynamic)
            if not known and f.endswith(tuple(app.cfg.get("unknown_file_full_exts", []))):
                return full(f"changed file not in any dependency graph: {f}")
        selected |= hits

    # Without a fresh dynamic map, widen: also run tests in the mirrored package/directory of each changed
    # source (catches reflection, DI wiring and other edges invisible to import analysis).
    if dynamic is None and settings.get("widen_without_coverage", True):
        mirrors = app.cfg.get("mirror", {})
        for f in relevant:
            loc = app.local(f)
            for src_prefix, test_prefix in mirrors.items():
                if not loc.startswith(src_prefix):
                    continue
                sub = loc[len(src_prefix):]
                if "/" in sub:
                    folder = test_prefix + sub.rsplit("/", 1)[0] + "/"
                    selected |= {t for t in all_tests if app.local(t).startswith(folder)}
                else:
                    # file at the top of the source tree: only tests directly in the mirrored folder
                    top = test_prefix.rstrip("/")
                    selected |= {t for t in all_tests
                                 if app.local(t).rsplit("/", 1)[0] == top and app.local(t).count("/") == top.count("/") + 1}
        d.reasons.append("widened to mirrored test packages (no fresh coverage map)")

    # Suites that boot the whole application (e.g. @SpringBootTest) run in full on any source change.
    source_changed = [f for f in relevant if f not in all_tests]
    for suite in app.cfg.get("full_suite_on_source_change", []):
        if source_changed and suite in suites:
            selected |= set(suites[suite])
            d.reasons.append(f"suite '{suite}' runs in full on any source change")

    for suite, smoke in app.cfg.get("smoke", {}).items():
        for s in smoke:
            path = f"{app.root}/{s}"
            if path in all_tests:
                selected.add(path)

    d.suites = {s: sorted(app.unit(t) for t in ts if t in selected) for s, ts in suites.items()}
    d.mode = "subset" if any(d.suites.values()) else "none"
    d.reasons.append(f"{len(relevant)} relevant changed files -> {len(selected)} test files")
    return d


def select(repo: Path, config: dict, changed: list[str], now: float | None = None,
           use_dynamic: bool = True, force_full: str | None = None) -> dict:
    settings = config.get("settings", {})
    apps = [App(a, repo) for a in config["app"]]
    decisions = [decide(a, changed, settings, now, use_dynamic, force_full).to_dict() for a in apps]
    return {"changed": changed, "apps": {d["app"]: d for d in decisions}}


def normalize(paths: list[str]) -> list[str]:
    return [PurePosixPath(p.replace("\\", "/")).as_posix() for p in paths]
