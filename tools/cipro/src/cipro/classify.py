"""Classify workflow step names into waste buckets."""
from __future__ import annotations

import re

# Order matters: first match wins.
RULES: list[tuple[str, re.Pattern[str]]] = [
    ("runner-overhead", re.compile(r"^(set up job|complete job|post |stop containers|initialize containers)", re.I)),
    ("checkout", re.compile(r"checkout", re.I)),
    ("cache", re.compile(r"\bcache\b", re.I)),
    ("toolchain", re.compile(r"^(set ?up|install) (java|jdk|node|python|go|docker buildx|qemu)", re.I)),
    ("publish", re.compile(r"(push|publish|upload|deploy|log ?in to|login)", re.I)),
    ("image-build", re.compile(r"(docker|image|buildx)", re.I)),
    ("install", re.compile(r"(install|npm ci|pip |restore|dependencies|download)", re.I)),
    ("lint", re.compile(r"(lint|typecheck|ruff|eslint|format|style|verify generated|codegen)", re.I)),
    ("test", re.compile(r"(test|e2e|pytest|vitest|playwright|verify|junit|shard)", re.I)),
    ("build", re.compile(r"(build|compile|package|bundle)", re.I)),
]

CATEGORIES = [c for c, _ in RULES] + ["other"]


def classify(step_name: str | None) -> str:
    name = (step_name or "").strip()
    for category, pattern in RULES:
        if pattern.search(name):
            return category
    return "other"


# Buckets that do not produce a quality signal; the dissertation calls these "overhead".
OVERHEAD = {"runner-overhead", "checkout", "cache", "toolchain", "install"}
