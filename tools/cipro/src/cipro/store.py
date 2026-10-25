"""SQLite storage for runs, jobs, steps, timings and log-derived events."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  workflow TEXT NOT NULL,
  name TEXT,
  head_sha TEXT,
  head_branch TEXT,
  event TEXT,
  status TEXT,
  conclusion TEXT,
  run_attempt INTEGER,
  created_at TEXT,
  run_started_at TEXT,
  updated_at TEXT,
  html_url TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL,
  name TEXT,
  status TEXT,
  conclusion TEXT,
  created_at TEXT,
  started_at TEXT,
  completed_at TEXT,
  runner_name TEXT,
  runner_group_name TEXT,
  labels TEXT
);
CREATE TABLE IF NOT EXISTS steps (
  job_id INTEGER NOT NULL,
  number INTEGER NOT NULL,
  name TEXT,
  status TEXT,
  conclusion TEXT,
  started_at TEXT,
  completed_at TEXT,
  PRIMARY KEY (job_id, number)
);
CREATE TABLE IF NOT EXISTS run_timing (
  run_id INTEGER PRIMARY KEY,
  run_duration_ms INTEGER,
  billable_json TEXT
);
CREATE TABLE IF NOT EXISTS log_events (
  job_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  detail TEXT,
  value REAL
);
CREATE TABLE IF NOT EXISTS logs_fetched (
  job_id INTEGER PRIMARY KEY
);
CREATE INDEX IF NOT EXISTS ix_runs_wf ON runs(workflow, head_sha);
CREATE INDEX IF NOT EXISTS ix_jobs_run ON jobs(run_id);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def upsert_run(con: sqlite3.Connection, workflow: str, r: dict) -> None:
    con.execute(
        "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            r["id"], workflow, r.get("name"), r.get("head_sha"), r.get("head_branch"), r.get("event"),
            r.get("status"), r.get("conclusion"), r.get("run_attempt"), r.get("created_at"),
            r.get("run_started_at"), r.get("updated_at"), r.get("html_url"),
        ),
    )


def upsert_jobs(con: sqlite3.Connection, run_id: int, jobs: list[dict]) -> None:
    for j in jobs:
        con.execute(
            "INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                j["id"], run_id, j.get("name"), j.get("status"), j.get("conclusion"), j.get("created_at"),
                j.get("started_at"), j.get("completed_at"), j.get("runner_name"),
                j.get("runner_group_name"), json.dumps(j.get("labels") or []),
            ),
        )
        con.execute("DELETE FROM steps WHERE job_id = ?", (j["id"],))
        for s in j.get("steps") or []:
            con.execute(
                "INSERT INTO steps VALUES (?,?,?,?,?,?,?)",
                (j["id"], s["number"], s.get("name"), s.get("status"), s.get("conclusion"),
                 s.get("started_at"), s.get("completed_at")),
            )


def upsert_timing(con: sqlite3.Connection, run_id: int, timing: dict | None) -> None:
    if timing is None:
        return
    con.execute(
        "INSERT OR REPLACE INTO run_timing VALUES (?,?,?)",
        (run_id, timing.get("run_duration_ms"), json.dumps(timing.get("billable") or {})),
    )


def have_run(con: sqlite3.Connection, run_id: int) -> bool:
    return con.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone() is not None


def logs_done(con: sqlite3.Connection, job_id: int) -> bool:
    return con.execute("SELECT 1 FROM logs_fetched WHERE job_id=?", (job_id,)).fetchone() is not None


def replace_log_events(
    con: sqlite3.Connection, job_id: int, events: list[tuple[str, str, float | None]]
) -> None:
    con.execute("DELETE FROM log_events WHERE job_id=?", (job_id,))
    con.executemany("INSERT INTO log_events VALUES (?,?,?,?)", [(job_id, k, d, v) for k, d, v in events])
    con.execute("INSERT OR REPLACE INTO logs_fetched VALUES (?)", (job_id,))
