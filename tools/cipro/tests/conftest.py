from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from cipro import store
from cipro.github import Response

T0 = datetime(2026, 10, 25, 10, 0, 0, tzinfo=timezone.utc)


def iso(seconds: float) -> str:
    return (T0 + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_job(job_id, name, created, started, completed, steps, conclusion="success", labels=("ubuntu-latest",)):
    return {
        "id": job_id, "name": name, "status": "completed", "conclusion": conclusion,
        "created_at": iso(created), "started_at": iso(started), "completed_at": iso(completed),
        "runner_name": "GitHub Actions 1", "runner_group_name": "GitHub Actions", "labels": list(labels),
        "steps": [
            {"number": i + 1, "name": n, "status": "completed", "conclusion": "success",
             "started_at": iso(a), "completed_at": iso(b)}
            for i, (n, a, b) in enumerate(steps)
        ],
    }


def make_run(run_id, sha, offset=0.0, branch="main", conclusion="success"):
    return {
        "id": run_id, "name": "ci", "head_sha": sha, "head_branch": branch, "event": "push",
        "status": "completed", "conclusion": conclusion, "run_attempt": 1,
        "created_at": iso(offset), "run_started_at": iso(offset), "updated_at": iso(offset + 900),
        "html_url": f"https://github.com/o/r/actions/runs/{run_id}",
    }


def sequential_jobs(base_id, offset, scale=1.0):
    """One job: setup 30s, install 120s, test 300s*scale, docker 200s, push 30s."""
    o = offset
    s = [
        ("Set up job", o + 5, o + 10),
        ("Checkout", o + 10, o + 15),
        ("Set up Java 21", o + 15, o + 45),
        ("web - install", o + 45, o + 165),
        ("orders-api - build and test", o + 165, o + 165 + 300 * scale),
    ]
    e = o + 165 + 300 * scale
    s += [("Build images", e, e + 200), ("Push images", e + 200, e + 230), ("Complete job", e + 230, e + 231)]
    return [make_job(base_id, "build-test-publish", o, o + 5, e + 231, s)]


def dag_jobs(base_id, offset):
    """changes -> (unit, e2e in parallel) -> publish."""
    o = offset
    return [
        make_job(base_id, "changes", o, o + 3, o + 20, [("Set up job", o + 3, o + 5), ("Checkout", o + 5, o + 10)]),
        make_job(base_id + 1, "unit", o + 20, o + 25, o + 200, [("unit tests", o + 30, o + 195)]),
        make_job(base_id + 2, "e2e", o + 20, o + 28, o + 260, [("e2e tests", o + 30, o + 255)]),
        make_job(base_id + 3, "publish", o + 260, o + 270, o + 330, [("Push images", o + 275, o + 325)]),
        make_job(base_id + 4, "docs", o + 20, o + 20, o + 20, [], conclusion="skipped"),
    ]


@pytest.fixture
def con():
    c = store.connect(":memory:")
    yield c
    c.close()


@pytest.fixture
def populated(con):
    """Five baseline runs and five optimized runs on the same five shas."""
    for i in range(5):
        sha = f"sha{i}"
        r = make_run(100 + i, sha, offset=i * 3600)
        store.upsert_run(con, "ci-baseline.yml", r)
        store.upsert_jobs(con, r["id"], sequential_jobs(1000 + i * 10, i * 3600, scale=1 + i * 0.1))
        r2 = make_run(200 + i, sha, offset=i * 3600 + 60)
        store.upsert_run(con, "ci-optimized.yml", r2)
        store.upsert_jobs(con, r2["id"], dag_jobs(2000 + i * 10, i * 3600 + 60))
    # a failed baseline run that must be excluded by default
    bad = make_run(999, "shaX", offset=99999, conclusion="failure")
    store.upsert_run(con, "ci-baseline.yml", bad)
    store.upsert_jobs(con, 999, sequential_jobs(9990, 99999))
    con.commit()
    return con


class FakeTransport:
    """Routes URLs to canned responses; records calls."""

    def __init__(self, routes: dict[str, list[Response] | Response]):
        self.routes = routes
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        for prefix, resp in self.routes.items():
            if url.startswith(prefix):
                if isinstance(resp, list):
                    return resp.pop(0) if len(resp) > 1 else resp[0]
                return resp
        return Response(404, {}, b'{"message":"Not Found"}')


def jresp(obj, status=200, headers=None):
    return Response(status, headers or {}, json.dumps(obj).encode())
