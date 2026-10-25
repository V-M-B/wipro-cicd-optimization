"""Extract cache events and test counts from raw GitHub Actions job logs."""
from __future__ import annotations

import re

TS_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s?")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("cache_hit", re.compile(r"Cache restored from key:\s*(\S+)")),
    ("cache_miss", re.compile(r"Cache not found for input keys:\s*(.+)")),
    ("cache_saved", re.compile(r"Cache saved with key:\s*(\S+)")),
    ("docker_layer_cached", re.compile(r"^#\d+ CACHED")),
    ("docker_cache_import", re.compile(r"importing cache manifest from (\S+)")),
]

MAVEN_SUMMARY = re.compile(
    r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)(?!, Time elapsed)\s*$"
)
VITEST_SUMMARY = re.compile(r"^\s*Tests\s+(?:(\d+) failed \| )?(\d+) passed")
PLAYWRIGHT_SUMMARY = re.compile(r"^\s*(\d+) passed \(([\d.]+)(m|s)\)")
PYTEST_SUMMARY = re.compile(r"^=+ (.*\b(?:passed|failed)\b.*) in ([\d.]+)s")


def strip(line: str) -> str:
    return ANSI.sub("", TS_PREFIX.sub("", line.rstrip("\r\n")))


def parse(log_text: str) -> list[tuple[str, str, float | None]]:
    """Return (kind, detail, value) events."""
    events: list[tuple[str, str, float | None]] = []
    for raw in log_text.splitlines():
        line = strip(raw)
        for kind, pat in PATTERNS:
            m = pat.search(line)
            if m:
                events.append((kind, m.group(1) if m.groups() else line[:120], None))
        m = MAVEN_SUMMARY.search(line)
        if m:
            events.append(("tests_maven", "total", float(m.group(1))))
            continue
        m = VITEST_SUMMARY.search(line)
        if m:
            failed = int(m.group(1) or 0)
            events.append(("tests_vitest", "total", float(failed + int(m.group(2)))))
            continue
        m = PLAYWRIGHT_SUMMARY.search(line)
        if m:
            events.append(("tests_playwright", "total", float(m.group(1))))
            continue
        m = PYTEST_SUMMARY.search(line)
        if m:
            counts = re.findall(r"(\d+) (passed|failed|error|errors)", m.group(1))
            events.append(("tests_pytest", "total", float(sum(int(n) for n, _ in counts))))
    return events


def cache_hit_rate(events: list[tuple[str, str, float | None]]) -> float | None:
    hits = sum(1 for k, _, _ in events if k == "cache_hit")
    misses = sum(1 for k, _, _ in events if k == "cache_miss")
    return hits / (hits + misses) if hits + misses else None
