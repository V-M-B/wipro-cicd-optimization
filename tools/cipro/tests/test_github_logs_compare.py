import json

import pytest

from cipro import logs
from cipro.compare import compare, pair, to_markdown
from cipro.github import GitHub, GitHubError, Response
from cipro.metrics import workflow_runs

from .conftest import FakeTransport, jresp

API = "https://api.github.com/repos/o/r/"


def test_repo_validation():
    with pytest.raises(ValueError):
        GitHub("no-slash")


def test_headers_and_token():
    t = FakeTransport({API + "actions/runs/1/timing": jresp({"run_duration_ms": 1000})})
    gh = GitHub("o/r", token="tkn", transport=t)
    assert gh.run_timing(1) == {"run_duration_ms": 1000}
    url, headers = t.calls[0]
    assert headers["Authorization"] == "Bearer tkn"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"


def test_timing_missing_returns_none():
    gh = GitHub("o/r", transport=FakeTransport({}))
    assert gh.run_timing(5) is None


def test_pagination_and_limit():
    page1 = jresp({"workflow_runs": [{"id": i} for i in range(100)]})
    page2 = jresp({"workflow_runs": [{"id": 100 + i} for i in range(3)]})
    t = FakeTransport({API + "actions/workflows/ci.yml/runs": [page1, page2]})
    gh = GitHub("o/r", transport=t)
    ids = [r["id"] for r in gh.workflow_runs("ci.yml", branch="main", created=">=2026-01-01")]
    assert ids == list(range(103))
    assert "branch=main" in t.calls[0][0] and "status=completed" in t.calls[0][0]
    assert "page=2" in t.calls[1][0]

    t2 = FakeTransport({API + "actions/workflows/ci.yml/runs": jresp({"workflow_runs": [{"id": i} for i in range(100)]})})
    assert len(list(GitHub("o/r", transport=t2).workflow_runs("ci.yml", limit=7))) == 7


def test_retry_on_server_error_and_rate_limit():
    sleeps = []
    t = FakeTransport({API + "actions/runs/9/jobs": [
        Response(502, {}, b""),
        Response(403, {"x-ratelimit-remaining": "0"}, b""),
        jresp({"jobs": [{"id": 1}]}),
    ]})
    gh = GitHub("o/r", transport=t, sleep=sleeps.append)
    assert gh.run_jobs(9) == [{"id": 1}]
    assert sleeps == [2.0, 4.0]


def test_get_raises_on_error():
    gh = GitHub("o/r", transport=FakeTransport({}), sleep=lambda s: None)
    with pytest.raises(GitHubError):
        gh.get("actions/runs/1")


def test_job_log_follows_redirect_without_token():
    t = FakeTransport({
        API + "actions/jobs/7/logs": Response(302, {"location": "https://blob.example/log?sig=1"}, b""),
        "https://blob.example/": Response(200, {}, b"hello log"),
    })
    gh = GitHub("o/r", token="secret", transport=t)
    assert gh.job_log(7) == "hello log"
    assert "Authorization" not in t.calls[1][1]


def test_job_log_unavailable():
    gh = GitHub("o/r", transport=FakeTransport({API + "actions/jobs/8/logs": Response(410, {}, b"")}))
    assert gh.job_log(8) is None


SAMPLE_LOG = """2026-10-25T10:00:00.1234567Z Cache restored from key: setup-java-Linux-maven-abc123
2026-10-25T10:00:01.0000000Z Cache not found for input keys: node-cache-Linux-npm-def
2026-10-25T10:00:02.0000000Z Cache saved with key: node-cache-Linux-npm-def
2026-10-25T10:01:00.0000000Z #7 CACHED
2026-10-25T10:01:00.0000000Z #8 importing cache manifest from gha:123
2026-10-25T10:02:00.0000000Z [INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 1.2 s - in com.x.FooTest
2026-10-25T10:02:01.0000000Z [INFO] Tests run: 360, Failures: 0, Errors: 0, Skipped: 1
2026-10-25T10:03:00.0000000Z       Tests  2 failed | 598 passed (600)
2026-10-25T10:04:00.0000000Z   30 passed (1.4m)
2026-10-25T10:05:00.0000000Z ======================== 498 passed, 2 failed, 3 skipped in 45.21s ========================
"""


def test_log_parse():
    ev = logs.parse(SAMPLE_LOG)
    kinds = [k for k, _, _ in ev]
    assert kinds.count("cache_hit") == 1
    assert kinds.count("cache_miss") == 1
    assert kinds.count("cache_saved") == 1
    assert "docker_layer_cached" in kinds and "docker_cache_import" in kinds
    vals = {k: v for k, _, v in ev if k.startswith("tests_")}
    assert vals == {"tests_maven": 360, "tests_vitest": 600, "tests_playwright": 30, "tests_pytest": 500}
    assert logs.cache_hit_rate(ev) == 0.5
    assert logs.cache_hit_rate([]) is None


def test_compare_pairs_by_sha(populated):
    a = workflow_runs(populated, "ci-baseline.yml")
    b = workflow_runs(populated, "ci-optimized.yml")
    assert len(pair(a, b)) == 5
    res = compare(a, b)
    assert res["pairs"] == 5
    wall = next(r for r in res["rows"] if r["metric"] == "wall_clock_s")
    assert wall["b_p50"] < wall["a_p50"]
    assert wall["reduction_pct"] > 40
    lo, hi = wall["diff_ci95"]
    assert lo <= wall["diff_p50"] <= hi
    md = to_markdown(res, "ci-baseline.yml", "ci-optimized.yml")
    assert "| Wall-clock (s) |" in md and "Paired comparison on **5** commits" in md
    json.dumps(res)


def test_compare_no_overlap(populated):
    a = workflow_runs(populated, "ci-baseline.yml")
    res = compare(a, [])
    assert res["pairs"] == 0 and res["rows"] == []
