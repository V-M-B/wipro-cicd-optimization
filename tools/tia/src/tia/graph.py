"""Static dependency graphs (file -> files it depends on) for Java, TypeScript and Python sources.

The analysis is deliberately conservative: when in doubt it adds an edge. Missing edges cause unsafe test
selection; extra edges only cost test time.
"""
from __future__ import annotations

import ast
import re
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath


def rel(path: Path, root: Path) -> str:
    return PurePosixPath(path.resolve().relative_to(root.resolve()).as_posix()).as_posix()


# ----------------------------------------------------------------------------- Java
JAVA_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
JAVA_IMPORT = re.compile(r"^\s*import\s+(static\s+)?([\w.]+)(\.\*)?\s*;", re.M)
JAVA_IDENT = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")


def java_graph(files: list[Path], repo: Path) -> dict[str, set[str]]:
    """Edges: imports (exact class, wildcard package, static member owner) and same-package type references."""
    by_fqn: dict[str, str] = {}
    by_pkg: dict[str, dict[str, str]] = defaultdict(dict)
    texts: dict[str, str] = {}
    pkgs: dict[str, str] = {}
    for f in files:
        r = rel(f, repo)
        text = f.read_text(encoding="utf-8", errors="replace")
        texts[r] = text
        m = JAVA_PACKAGE.search(text)
        pkg = m.group(1) if m else ""
        pkgs[r] = pkg
        cls = f.stem
        by_fqn[f"{pkg}.{cls}" if pkg else cls] = r
        by_pkg[pkg][cls] = r
    graph: dict[str, set[str]] = {}
    for r, text in texts.items():
        deps: set[str] = set()
        idents = set(JAVA_IDENT.findall(text))
        for static, name, star in JAVA_IMPORT.findall(text):
            if star:
                # wildcard: package.* or static Class.*
                if name in by_fqn:
                    deps.add(by_fqn[name])
                for cls, target in by_pkg.get(name, {}).items():
                    if cls in idents:
                        deps.add(target)
                continue
            target = by_fqn.get(name)
            if target is None and static:
                target = by_fqn.get(name.rsplit(".", 1)[0])
            if target is None:
                # nested class import: com.x.Outer.Inner -> Outer
                parent = name.rsplit(".", 1)[0]
                target = by_fqn.get(parent)
            if target:
                deps.add(target)
        for cls, target in by_pkg.get(pkgs[r], {}).items():
            if target != r and cls in idents:
                deps.add(target)
        deps.discard(r)
        graph[r] = deps
    return graph


# ----------------------------------------------------------------------------- TypeScript
TS_IMPORT = re.compile(
    r"""(?:import|export)\s+(?:type\s+)?(?:[\w*{}\s,]+\s+from\s+)?["']([^"']+)["']"""
    r"""|import\(\s*["']([^"']+)["']\s*\)"""
    r"""|vi\.mock\(\s*["']([^"']+)["']"""
)
TS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".css", ".json")


def _resolve_ts(spec: str, importer: Path, aliases: dict[str, Path]) -> Path | None:
    base: Path | None = None
    if spec.startswith("."):
        base = (importer.parent / spec)
    else:
        for prefix, target in aliases.items():
            if spec == prefix or spec.startswith(prefix.rstrip("/") + "/"):
                base = target / spec[len(prefix):].lstrip("/")
                break
    if base is None:
        return None  # bare package import
    candidates = [base] + [base.with_name(base.name + e) for e in TS_EXTS] + [base / f"index{e}" for e in TS_EXTS]
    for c in candidates:
        if c.is_file():
            return c
    return None


def ts_graph(files: list[Path], repo: Path, aliases: dict[str, Path] | None = None) -> dict[str, set[str]]:
    aliases = aliases or {}
    graph: dict[str, set[str]] = {}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        deps = set()
        for groups in TS_IMPORT.findall(text):
            spec = next(g for g in groups if g)
            target = _resolve_ts(spec, f, aliases)
            if target is not None:
                deps.add(rel(target, repo))
        graph[rel(f, repo)] = deps
    return graph


# ----------------------------------------------------------------------------- Python
def _py_module_index(files: list[Path], roots: list[Path]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for f in files:
        for root in roots:
            try:
                parts = list(f.resolve().relative_to(root.resolve()).with_suffix("").parts)
            except ValueError:
                continue
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                index[".".join(parts)] = f
    return index


def _py_package(f: Path, root: Path) -> list[str]:
    parts = list(f.resolve().relative_to(root.resolve()).with_suffix("").parts)
    return parts[:-1]


def python_graph(files: list[Path], repo: Path, roots: list[Path]) -> dict[str, set[str]]:
    index = _py_module_index(files, roots)
    graph: dict[str, set[str]] = {}
    for f in files:
        deps: set[str] = set()
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            graph[rel(f, repo)] = deps
            continue
        root = next((r for r in roots if f.resolve().is_relative_to(r.resolve())), roots[0])
        pkg = _py_package(f, root)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = pkg[: len(pkg) - (node.level - 1)] if node.level > 1 else pkg
                    mod = ".".join(base + ([node.module] if node.module else []))
                else:
                    mod = node.module or ""
                names.append(mod)
                names += [f"{mod}.{a.name}" if mod else a.name for a in node.names]
        for name in names:
            # importing a.b.c also executes a/__init__ and a/b/__init__
            parts = name.split(".")
            for i in range(1, len(parts) + 1):
                target = index.get(".".join(parts[:i]))
                if target is not None:
                    deps.add(rel(target, repo))
        deps.discard(rel(f, repo))
        graph[rel(f, repo)] = deps
    # conftest.py files apply to every test module beneath them
    conftests = [rel(f, repo) for f in files if f.name == "conftest.py"]
    for node in graph:
        for c in conftests:
            if node != c and node.startswith(c.rsplit("/", 1)[0] + "/"):
                graph[node].add(c)
    return graph


# ----------------------------------------------------------------------------- closure
def reachable(graph: dict[str, set[str]], start: str) -> set[str]:
    seen = {start}
    q = deque([start])
    while q:
        n = q.popleft()
        for d in graph.get(n, ()):
            if d not in seen:
                seen.add(d)
                q.append(d)
    return seen


def reverse_closure(graph: dict[str, set[str]], tests: list[str]) -> dict[str, set[str]]:
    """source file -> set of test files that (transitively) depend on it."""
    out: dict[str, set[str]] = defaultdict(set)
    for t in tests:
        for n in reachable(graph, t):
            out[n].add(t)
    return out
