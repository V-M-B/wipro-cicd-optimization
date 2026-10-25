import math

import pytest

from cipro.classify import classify
from cipro.metrics import (
    bootstrap_ci,
    load_pricing,
    median,
    percentile,
    rate_for,
    run_metrics,
    seconds,
    step_stats,
    summarize,
    workflow_runs,
)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Set up job", "runner-overhead"),
        ("Complete job", "runner-overhead"),
        ("Post Set up Java 21", "runner-overhead"),
        ("Checkout", "checkout"),
        ("Run actions/checkout@v4", "checkout"),
        ("Restore Maven cache", "cache"),
        ("Set up Java 21", "toolchain"),
        ("Set up Node 20", "toolchain"),
        ("Set up Python 3.12", "toolchain"),
        ("web - install", "install"),
        ("analytics - install", "install"),
        ("web - install Playwright browser", "install"),
        ("Shared schemas - verify generated code", "lint"),
        ("web - lint and typecheck", "lint"),
        ("analytics - lint", "lint"),
        ("orders-api - build and test", "test"),
        ("web - unit tests", "test"),
        ("web - e2e tests", "test"),
        ("analytics - tests", "test"),
        ("web - build", "build"),
        ("Build images", "image-build"),
        ("Push images", "publish"),
        ("Log in to GHCR", "publish"),
        ("Upload test reports", "publish"),
        ("something else", "other"),
        (None, "other"),
    ],
)
def test_classify(name, expected):
    assert classify(name) == expected


def test_percentile_and_median():
    assert percentile([], 50) is None
    assert percentile([7], 95) == 7
    assert median([1, 2, 3, 4]) == 2.5
    assert percentile([0, 10], 95) == pytest.approx(9.5)
    assert percentile([5, 1, 3], 0) == 1
    assert percentile([5, 1, 3], 100) == 5


def test_seconds_handles_missing():
    assert seconds(None, "2026-10-25T10:00:00Z") is None
    assert seconds("2026-10-25T10:00:00Z", "2026-10-25T10:01:30Z") == 90


def test_bootstrap_ci_contains_point_and_is_deterministic():
    a = [600, 620, 610, 640, 605, 630]
    b = [300, 310, 305, 320, 290, 315]
    p1 = bootstrap_ci(a, b, n=500)
    p2 = bootstrap_ci(a, b, n=500)
    assert p1 == p2
    point, lo, hi = p1
    assert lo <= point <= hi
    assert hi < 0  # clearly faster


def test_bootstrap_requires_pairs():
    with pytest.raises(ValueError):
        bootstrap_ci([1, 2], [1])


def test_rate_for_labels():
    pricing = load_pricing()
    assert rate_for(["ubuntu-latest"], pricing, False) == pricing["github_hosted"]["per_minute"]["ubuntu-latest"]
    assert rate_for(["ubuntu-24.04"], pricing, False) == pricing["github_hosted"]["per_minute"]["ubuntu-latest"]
    assert rate_for(["windows-2022"], pricing, False) == pricing["github_hosted"]["per_minute"]["windows-latest"]
    assert rate_for(["macos-14"], pricing, False) == pricing["github_hosted"]["per_minute"]["macos-latest"]
    assert rate_for(["linux-8core"], pricing, False) == pricing["github_hosted"]["per_minute"]["linux-8core"]
    assert rate_for(["mystery"], pricing, False) == pricing["github_hosted"]["per_minute"]["ubuntu-latest"]
    assert rate_for(["self-hosted", "arc"], pricing, False) == 0.0
    assert rate_for(["self-hosted"], pricing, True) == pricing["self_hosted"]["platform_fee_per_minute_scenario"]


def test_pricing_has_sources():
    pricing = load_pricing()
    assert pricing["github_hosted"]["source"].startswith("https://")
    assert pricing["github_hosted"]["checked"]
    assert pricing["self_hosted"]["platform_fee_source"].startswith("https://")


def test_sequential_run_metrics(populated):
    m = run_metrics(populated, 100)
    # job created at 0, started 5, completed 165+300+231 = 696
    assert m.wall_clock_s == 696
    assert m.exec_span_s == 691
    assert m.time_to_first_job_s == 5
    assert m.billable_min == math.ceil(691 / 60)
    assert m.cost_usd == pytest.approx(m.billable_min * 0.006)
    assert m.category_s["install"] == 120
    assert m.category_s["image-build"] == 200
    assert m.critical_path == ["build-test-publish"]
    assert 0 < m.overhead_share < 1


def test_dag_run_metrics_and_critical_path(populated):
    m = run_metrics(populated, 200)
    # created at 60, last completes at 60+330
    assert m.wall_clock_s == 330
    # skipped job not billed; others ceil per job: changes 17s->1, unit 175->3, e2e 232->4, publish 60->1
    assert m.billable_min == 1 + 3 + 4 + 1
    assert m.critical_path == ["changes", "e2e", "publish"]
    assert m.queue_total_s == 3 + 5 + 8 + 10


def test_workflow_runs_filters_failed(populated):
    assert len(workflow_runs(populated, "ci-baseline.yml")) == 5
    assert len(workflow_runs(populated, "ci-baseline.yml", success_only=False)) == 6
    assert len(workflow_runs(populated, "ci-baseline.yml", branch_glob="exp/*")) == 0
    assert len(workflow_runs(populated, "ci-baseline.yml", since="2026-10-25T12:00:00Z")) == 3  # 12:00, 13:00, 14:00 inclusive


def test_summarize(populated):
    s = summarize(workflow_runs(populated, "ci-baseline.yml"))
    assert s["runs"] == 5
    assert s["wall_clock_min_s"] <= s["wall_clock_p50_s"] <= s["wall_clock_p95_s"] <= s["wall_clock_max_s"]
    assert s["category_p50_s"]["image-build"] == 200
    assert s["cost_usd_per_1000_runs_p50"] == pytest.approx(s["cost_usd_p50"] * 1000)
    empty = summarize([])
    assert empty["runs"] == 0 and empty["wall_clock_p50_s"] is None


def test_step_stats(populated):
    ids = [r.id for r in workflow_runs(populated, "ci-baseline.yml")]
    stats = step_stats(populated, ids)
    top = stats[0]
    assert top["step"] == "orders-api - build and test"
    assert top["n"] == 5
    assert step_stats(populated, []) == []
