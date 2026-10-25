"""Run tia and expose the selection as GitHub Actions job outputs (used by ci-optimized.yml).

On main (or when --force-full is given) every suite runs: that is the safety net. On other branches the
selection is computed against the merge-base with origin/main.

Outputs (written to $GITHUB_OUTPUT, also printed):
  orders_unit, orders_it      comma-separated Java classes ('' = skip)
  web_unit, web_e2e           space-separated files relative to apps/web
  analytics                   space-separated files relative to apps/analytics
  <suite>_shards              JSON list of shard indices sized to the selection, e.g. [0,1]
  images                      JSON list of apps whose image must be rebuilt
  static                      'true' if lint/typecheck/codegen checks must run
  summary                     one-line human summary
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/tia/src"))

from tia.select import changed_files, select  # noqa: E402

MAX_SHARDS = {"orders_it": 2, "web_unit": 2, "analytics": 2, "orders_unit": 1, "web_e2e": 1}
MIN_UNITS_PER_SHARD = {"orders_it": 2, "web_unit": 6, "analytics": 6, "orders_unit": 1, "web_e2e": 1}


def merge_base(ref: str = "origin/main") -> str:
    return subprocess.run(["git", "merge-base", ref, "HEAD"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def shards(name: str, n_units: int) -> list[int]:
    if n_units == 0:
        return []
    k = max(1, min(MAX_SHARDS[name], n_units // MIN_UNITS_PER_SHARD[name]))
    return list(range(k))


def compute(force_full: str | None, base: str | None, use_dynamic: bool = True) -> dict:
    config = tomllib.loads((ROOT / "tia.toml").read_text(encoding="utf-8"))
    if force_full:
        res = select(ROOT, config, [], force_full=force_full, use_dynamic=use_dynamic)
    else:
        res = select(ROOT, config, changed_files(ROOT, base, "HEAD"), use_dynamic=use_dynamic)
    apps = res["apps"]
    o = apps["orders-api"]["suites"]
    w = apps["web"]["suites"]
    a = apps["analytics"]["suites"]
    out = {
        "orders_unit": ",".join(o.get("unit", [])),
        "orders_it": ",".join(o.get("integration", [])),
        "web_unit": " ".join(w.get("unit", [])),
        "web_e2e": " ".join(w.get("e2e", [])),
        "analytics": " ".join(a.get("unit", [])),
    }
    counts = {
        "orders_unit": len(o.get("unit", [])), "orders_it": len(o.get("integration", [])),
        "web_unit": len(w.get("unit", [])), "web_e2e": len(w.get("e2e", [])), "analytics": len(a.get("unit", [])),
    }
    for k, n in counts.items():
        out[f"{k}_shards"] = json.dumps(shards(k, n))
    images = [name for name, d in apps.items() if d["mode"] != "none"]
    out["images"] = json.dumps(images)
    changed = res["changed"]
    schema_touched = any(p.startswith("libs/shared-schemas/") or "/generated/" in p or "/schemas/" in p for p in changed)
    out["static"] = "true" if (images or schema_touched or force_full) else ""
    out["summary"] = "; ".join(
        f"{name}={d['mode']}({','.join(f'{s}:{n}/{d['total_units'].get(s, 0)}' for s, n in d['selected_units'].items())})"
        for name, d in apps.items())
    out["selection_json"] = json.dumps(res)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-full")
    ap.add_argument("--base")
    ap.add_argument("--static-only", action="store_true")
    a = ap.parse_args()
    ref = os.environ.get("GITHUB_REF", "")
    force = a.force_full or ("main branch safety net" if ref == "refs/heads/main" else None)
    base = a.base or (None if force else merge_base())
    out = compute(force, base, use_dynamic=not a.static_only)
    sel = out.pop("selection_json")
    (ROOT / "tia-selection.json").write_text(sel, encoding="utf-8")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{k}={v}" for k, v in out.items()]
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
