"""Generate synthetic regression faults (single-site mutations) as patch files for the TIA safety study.

Each fault is one mutation in one production source file, written as a unified diff under
experiments/faults/<app>/<id>.patch, plus experiments/faults/manifest.json describing all faults.

Operators (applied to code, not comments or strings, best effort):
  relational flip   ==  ->  !=      <=  ->  <      >=  ->  >      <  ->  <=      >  ->  >=
  logical flip      &&  ->  ||      and ->  or
  boolean flip      true -> false   True -> False
  off-by-one        + 1 -> + 2      - 1 -> - 2
  constant change   0.05 -> 0.06 style: last digit of a decimal literal incremented
  negation removal  !x  ->  x       not x -> x

Usage:
  python scripts/inject_faults.py --per-app 20 --seed 7
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

APPS = {
    "orders-api": {"glob": "apps/orders-api/src/main/java/com/retailops/orders/**/*.java", "lang": "java"},
    "web": {"glob": "apps/web/src/lib/**/*.ts", "lang": "ts"},
    "analytics": {"glob": "apps/analytics/app/**/*.py", "lang": "python"},
}
EXCLUDE = re.compile(r"(generated|/schemas/|__init__\.py$|\.d\.ts$|\.test\.)")

C_LIKE = [
    ("relational", r"(?<![=!<>])==(?!=)", "!="),
    ("relational", r"(?<![=!])!=(?!=)", "=="),
    ("relational", r"(?<![<>=])<=(?!=)", "<"),
    ("relational", r"(?<![<>=])>=(?!=)", ">"),
    ("relational", r"(?<=\s)<(?=\s)", "<="),
    ("relational", r"(?<=\s)>(?=\s)", ">="),
    ("logical", r"&&", "||"),
    ("logical", r"\|\|", "&&"),
    ("boolean", r"\btrue\b", "false"),
    ("boolean", r"\bfalse\b", "true"),
    ("off-by-one", r"\+ 1\b", "+ 2"),
    ("off-by-one", r"- 1\b", "- 2"),
    ("negation", r"(?<=[(\s])!(?=[A-Za-z_(])", ""),
]
PYTHON = [
    ("relational", r"(?<![=!<>])==(?!=)", "!="),
    ("relational", r"!=", "=="),
    ("relational", r"(?<![<>=])<=", "<"),
    ("relational", r"(?<![<>=])>=", ">"),
    ("relational", r"(?<=\s)<(?=\s)", "<="),
    ("relational", r"(?<=\s)>(?=\s)", ">="),
    ("logical", r"\band\b", "or"),
    ("logical", r"\bor\b", "and"),
    ("boolean", r"\bTrue\b", "False"),
    ("boolean", r"\bFalse\b", "True"),
    ("off-by-one", r"\+ 1\b", "+ 2"),
    ("off-by-one", r"- 1\b", "- 2"),
    ("negation", r"\bnot (?=[A-Za-z_(])", ""),
]
DECIMAL = re.compile(r"(?<![\w.])(\d+\.\d*[1-8])(?![\w.])")


def code_lines(text: str, lang: str):
    """Yield (index, line) for lines that look like code (skip comments, imports, annotations, strings-only)."""
    in_block = False
    for i, line in enumerate(text.splitlines(keepends=True)):
        s = line.strip()
        if lang in ("java", "ts"):
            if in_block:
                if "*/" in s:
                    in_block = False
                continue
            if s.startswith("/*"):
                in_block = "*/" not in s
                continue
            if s.startswith(("//", "*", "import ", "package ", "@")):
                continue
        else:
            if s.startswith(("#", "import ", "from ", '"""', "'''", "@")):
                continue
        if not s:
            continue
        yield i, line


def strip_strings(line: str) -> str:
    """Mask string literals so operators inside them are not mutated."""
    return re.sub(r"(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`[^`]*`)", lambda m: "\0" * len(m.group(0)), line)


def candidates(text: str, lang: str) -> list[tuple[int, int, int, str, str]]:
    ops = PYTHON if lang == "python" else C_LIKE
    out = []
    for i, line in code_lines(text, lang):
        masked = strip_strings(line.split("//")[0] if lang != "python" else line.split("#")[0])
        for kind, pat, repl in ops:
            for m in re.finditer(pat, masked):
                out.append((i, m.start(), m.end(), repl, kind))
        for m in DECIMAL.finditer(masked):
            lit = m.group(1)
            out.append((i, m.start(), m.end(), lit[:-1] + str(int(lit[-1]) + 1), "constant"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-app", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="experiments/faults")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out_dir = ROOT / a.out
    manifest = []
    for app, spec in APPS.items():
        files = sorted(p for p in ROOT.glob(spec["glob"]) if not EXCLUDE.search(p.as_posix()))
        pool = []
        for f in files:
            text = f.read_text(encoding="utf-8")
            pool += [(f, text, c) for c in candidates(text, spec["lang"])]
        rng.shuffle(pool)
        chosen, used_lines = [], set()
        kinds_seen: dict[str, int] = {}
        # prefer diversity of operators and files: at most per_app/4 of one kind
        for f, text, (i, s, e, repl, kind) in pool:
            if len(chosen) >= a.per_app:
                break
            if (f, i) in used_lines or kinds_seen.get(kind, 0) >= max(1, a.per_app // 4):
                continue
            used_lines.add((f, i))
            kinds_seen[kind] = kinds_seen.get(kind, 0) + 1
            chosen.append((f, text, i, s, e, repl, kind))
        for n, (f, text, i, s, e, repl, kind) in enumerate(chosen, 1):
            lines = text.splitlines(keepends=True)
            original = lines[i]
            lines[i] = original[:s] + repl + original[e:]
            relpath = f.relative_to(ROOT).as_posix()
            diff = "".join(difflib.unified_diff(text.splitlines(keepends=True), lines,
                                                fromfile=f"a/{relpath}", tofile=f"b/{relpath}"))
            fid = f"{app}-{n:02d}"
            patch = out_dir / app / f"{fid}.patch"
            patch.parent.mkdir(parents=True, exist_ok=True)
            patch.write_text(diff, encoding="utf-8", newline="\n")
            manifest.append({"id": fid, "app": app, "file": relpath, "line": i + 1, "operator": kind,
                             "before": original.strip(), "after": lines[i].strip(),
                             "patch": patch.relative_to(ROOT).as_posix()})
        print(f"{app}: {len(chosen)} faults from {len(files)} files ({len(pool)} candidate sites)")
    (out_dir / "manifest.json").write_text(json.dumps({"seed": a.seed, "faults": manifest}, indent=2),
                                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
