"""Replay curated experiment commits onto exp/* branches so every pipeline variant runs on identical inputs.

Each entry in experiments/commits/manifest.toml names a patch file. For each entry the script:
  1. creates branch exp/<run-label>/<id> from --base (default: the tag given, or main),
  2. applies the patch with `git apply`, commits it,
  3. pushes the branch (which triggers every workflow listening on exp/**),
  4. waits until all expected workflows have completed for that commit before moving to the next one
     (--parallel N allows N commits in flight).

Usage:
  python scripts/replay.py --label r1 --workflows ci-baseline.yml ci-optimized.yml [--only 1-5] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "experiments/commits/manifest.toml"


def sh(*args: str, check: bool = True, capture: bool = True) -> str:
    r = subprocess.run(args, cwd=ROOT, capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    return (r.stdout or "").strip()


def repo_slug() -> str:
    return sh("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")


def runs_for_sha(repo: str, sha: str) -> list[dict]:
    out = sh("gh", "api", f"repos/{repo}/actions/runs?head_sha={sha}&per_page=100")
    return json.loads(out)["workflow_runs"]


def wait_for(repo: str, sha: str, workflows: list[str], poll_s: int, timeout_s: int) -> dict[str, str]:
    deadline = time.time() + timeout_s
    while True:
        runs = runs_for_sha(repo, sha)
        state = {}
        for wf in workflows:
            mine = [r for r in runs if r["path"].endswith("/" + wf)]
            state[wf] = mine[0]["conclusion"] if mine and mine[0]["status"] == "completed" else "pending"
        if all(v != "pending" for v in state.values()):
            return state
        if time.time() > deadline:
            return state
        time.sleep(poll_s)


def select(entries: list[dict], only: str | None) -> list[dict]:
    if not only:
        return entries
    wanted: set[int] = set()
    for part in only.split(","):
        if "-" in part:
            a, b = part.split("-")
            wanted |= set(range(int(a), int(b) + 1))
        else:
            wanted.add(int(part))
    return [e for e in entries if int(e["id"]) in wanted]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="replay round label, e.g. r1")
    ap.add_argument("--workflows", nargs="+", required=True)
    ap.add_argument("--base", default="main", help="ref the experiment branches start from")
    ap.add_argument("--only", help="ids to replay, e.g. 1-5,9")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--poll", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=3 * 3600)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    manifest = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = select(manifest["commit"], a.only)
    if sh("git", "status", "--porcelain"):
        raise SystemExit("working tree not clean")
    start_branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD")
    repo = "DRY/RUN" if a.dry_run else repo_slug()
    log_path = ROOT / f"experiments/results/replay-{a.label}.jsonl"
    in_flight: list[tuple[dict, str]] = []

    def drain(limit: int) -> None:
        while len(in_flight) > limit:
            e, sha = in_flight.pop(0)
            state = {wf: "dry-run" for wf in a.workflows} if a.dry_run else wait_for(
                repo, sha, a.workflows, a.poll, a.timeout)
            rec = {"label": a.label, "id": e["id"], "category": e["category"], "sha": sha, "state": state,
                   "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            print(json.dumps(rec))
            if not a.dry_run:
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")

    try:
        for e in entries:
            branch = f"exp/{a.label}/{int(e['id']):02d}-{e['category']}"
            patch = ROOT / "experiments/commits" / e["patch"]
            sh("git", "checkout", "-q", "-B", branch, a.base)
            sh("git", "apply", "--whitespace=nowarn", str(patch))
            sh("git", "add", "-A")
            sh("git", "commit", "-q", "-m", f"experiment {a.label} #{e['id']} ({e['category']}): {e['title']}")
            sha = sh("git", "rev-parse", "HEAD")
            if a.dry_run:
                print(f"[dry-run] {branch} {sha[:8]} {e['title']}")
            else:
                sh("git", "push", "-q", "-f", "origin", branch)
                print(f"pushed {branch} {sha[:8]}")
            in_flight.append((e, sha))
            sh("git", "checkout", "-q", start_branch)
            drain(a.parallel - 1)
        drain(0)
    finally:
        sh("git", "checkout", "-q", start_branch, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
