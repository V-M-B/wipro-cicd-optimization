"""cipro command-line interface."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import logs as logparse
from . import report, store
from .compare import compare, to_markdown
from .github import GitHub, resolve_token
from .metrics import step_stats, summarize, workflow_runs

DEFAULT_DB = "experiments/results/cipro.sqlite"
DEFAULT_RAW = "experiments/results/raw"


def _gh(args) -> GitHub:
    return GitHub(args.repo, token=resolve_token())


def cmd_fetch(args) -> int:
    gh = _gh(args)
    con = store.connect(args.db)
    new = 0
    for wf in args.workflow:
        for run in gh.workflow_runs(wf, branch=args.branch, limit=args.last, created=args.created):
            if store.have_run(con, run["id"]) and not args.refresh:
                continue
            jobs = gh.run_jobs(run["id"])
            timing = gh.run_timing(run["id"])
            _ingest(con, wf, run, jobs, timing)
            raw = Path(args.raw_dir) / wf / f"{run['id']}-{run.get('run_attempt', 1)}.json"
            if not raw.exists():
                raw.parent.mkdir(parents=True, exist_ok=True)
                raw.write_text(json.dumps({"workflow": wf, "run": run, "jobs": jobs, "timing": timing}),
                               encoding="utf-8")
            new += 1
            print(f"  {wf} run {run['id']} {run.get('head_branch')} {run.get('conclusion')}")
    print(f"fetched {new} new runs into {args.db} (raw JSON in {args.raw_dir})")
    return 0


def _ingest(con, wf, run, jobs, timing) -> None:
    store.upsert_run(con, wf, run)
    store.upsert_jobs(con, run["id"], jobs)
    store.upsert_timing(con, run["id"], timing)
    con.commit()


def cmd_rebuild(args) -> int:
    """Rebuild the SQLite database from archived raw API JSON (offline, reproducible)."""
    con = store.connect(args.db)
    n = 0
    for path in sorted(Path(args.raw_dir).rglob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        _ingest(con, d["workflow"], d["run"], d["jobs"], d.get("timing"))
        n += 1
    print(f"rebuilt {args.db} from {n} raw run files")
    return 0


def cmd_logs(args) -> int:
    gh = _gh(args)
    con = store.connect(args.db)
    sql = "SELECT j.id FROM jobs j JOIN runs r ON r.id=j.run_id WHERE j.conclusion IS NOT NULL AND j.conclusion != 'skipped'"
    params: list = []
    if args.workflow:
        sql += f" AND r.workflow IN ({','.join('?' * len(args.workflow))})"
        params += args.workflow
    done = 0
    for (job_id,) in con.execute(sql, params).fetchall():
        if store.logs_done(con, job_id) and not args.refresh:
            continue
        text = gh.job_log(job_id)
        if text is None:
            print(f"  job {job_id}: log unavailable (expired or no permission)")
            continue
        store.replace_log_events(con, job_id, logparse.parse(text))
        con.commit()
        done += 1
    print(f"parsed logs for {done} jobs")
    return 0


def _load(con, wf, args):
    return workflow_runs(con, wf, branch_glob=args.branch_glob, success_only=not args.include_failed, since=args.since)


def cmd_summary(args) -> int:
    con = store.connect(args.db)
    out = {wf: summarize(_load(con, wf, args)) for wf in args.workflow}
    print(json.dumps(out, indent=2))
    return 0


def cmd_report(args) -> int:
    con = store.connect(args.db)
    wfs = {wf: _load(con, wf, args) for wf in args.workflow}
    pairs = [tuple(p.split(":", 1)) for p in args.pair or []]
    path = report.build(con, wfs, Path(args.out), title=args.title, repo=args.repo or "", pairs=pairs)
    print(f"wrote {path}")
    return 0


def cmd_compare(args) -> int:
    con = store.connect(args.db)
    res = compare(_load(con, args.a, args), _load(con, args.b, args))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(to_markdown(res, args.a, args.b))
    return 0 if res["pairs"] else 2


def cmd_export(args) -> int:
    """Write an immutable, timestamped export of the metrics for the selected workflows."""
    con = store.connect(args.db)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out) / f"{args.label}-{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    meta = {"label": args.label, "exported_at": stamp, "repo": args.repo, "workflows": args.workflow,
            "branch_glob": args.branch_glob, "since": args.since, "include_failed": args.include_failed}
    all_runs = []
    for wf in args.workflow:
        runs = _load(con, wf, args)
        all_runs += runs
        (out / f"{wf}.summary.json").write_text(json.dumps(summarize(runs), indent=2), encoding="utf-8")
        (out / f"{wf}.steps.json").write_text(
            json.dumps(step_stats(con, [r.id for r in runs]), indent=2), encoding="utf-8")
    with (out / "runs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "workflow", "head_sha", "head_branch", "conclusion", "created_at", "wall_clock_s",
                    "exec_span_s", "time_to_first_job_s", "queue_total_s", "job_seconds", "billable_min",
                    "cost_usd", "cost_usd_self_hosted_fee", "overhead_share", "critical_path"])
        for r in all_runs:
            w.writerow([r.id, r.workflow, r.head_sha, r.head_branch, r.conclusion, r.created_at, r.wall_clock_s,
                        r.exec_span_s, r.time_to_first_job_s, r.queue_total_s, r.job_seconds, r.billable_min,
                        r.cost_usd, r.cost_usd_self_hosted_fee, r.overhead_share, " > ".join(r.critical_path)])
    with (out / "jobs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "job_id", "name", "conclusion", "queue_s", "duration_s", "billable_min", "labels"])
        for r in all_runs:
            for j in r.jobs:
                w.writerow([r.id, j.id, j.name, j.conclusion, j.queue_s, j.duration_s, j.billable_min, "|".join(j.labels)])
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"exported {len(all_runs)} runs to {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cipro", description="CI profiler for GitHub Actions")
    p.add_argument("--db", default=DEFAULT_DB, help=f"SQLite path (default {DEFAULT_DB})")
    sub = p.add_subparsers(dest="cmd", required=True)

    def filters(sp):
        sp.add_argument("--branch-glob", help="SQLite GLOB on head_branch, e.g. 'exp/*'")
        sp.add_argument("--since", help="ISO timestamp lower bound on run created_at")
        sp.add_argument("--include-failed", action="store_true")

    f = sub.add_parser("fetch", help="pull runs/jobs/steps/timing from the GitHub API")
    f.add_argument("--repo", required=True)
    f.add_argument("--workflow", action="append", required=True, help="workflow file name, repeatable")
    f.add_argument("--branch")
    f.add_argument("--created", help="GitHub 'created' filter, e.g. '>=2026-10-25'")
    f.add_argument("--last", type=int, default=100)
    f.add_argument("--refresh", action="store_true")
    f.add_argument("--raw-dir", default=DEFAULT_RAW)
    f.set_defaults(func=cmd_fetch)

    rb = sub.add_parser("rebuild", help="rebuild the database from archived raw JSON")
    rb.add_argument("--raw-dir", default=DEFAULT_RAW)
    rb.set_defaults(func=cmd_rebuild)

    lg = sub.add_parser("logs", help="download job logs and extract cache/test events")
    lg.add_argument("--repo", required=True)
    lg.add_argument("--workflow", action="append")
    lg.add_argument("--refresh", action="store_true")
    lg.set_defaults(func=cmd_logs)

    s = sub.add_parser("summary", help="print summary metrics as JSON")
    s.add_argument("--workflow", action="append", required=True)
    filters(s)
    s.set_defaults(func=cmd_summary)

    r = sub.add_parser("report", help="write a static HTML report")
    r.add_argument("--workflow", action="append", required=True)
    r.add_argument("--out", default="docs/dashboard")
    r.add_argument("--title", default="CI pipeline profile")
    r.add_argument("--repo")
    r.add_argument("--pair", action="append", help="A:B workflow pair to compare, repeatable")
    filters(r)
    r.set_defaults(func=cmd_report)

    c = sub.add_parser("compare", help="paired comparison of two workflows on the same commits")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.add_argument("--json", help="also write the raw result as JSON")
    filters(c)
    c.set_defaults(func=cmd_compare)

    e = sub.add_parser("export", help="write immutable CSV/JSON export to experiments/results")
    e.add_argument("--workflow", action="append", required=True)
    e.add_argument("--label", required=True)
    e.add_argument("--out", default="experiments/results")
    e.add_argument("--repo")
    filters(e)
    e.set_defaults(func=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
