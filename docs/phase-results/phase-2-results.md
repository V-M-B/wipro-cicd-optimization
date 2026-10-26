# Phase 2 results — caching (`ci-cache.yml`)

**Status:** complete. Tag `opt-cache-v1` points at the commit where `ci-cache.yml` was frozen for replay round A.

## What the stage changes

Compared with the frozen baseline, `ci-cache.yml` keeps the same single sequential job and the same build and test
commands. It adds:

- Maven, npm and pip download caches (`setup-java` / `setup-node` / `setup-python`, keyed by `pom.xml`,
  `package-lock.json` and `requirements*.txt`);
- a Playwright browser-binary cache keyed by the Playwright version. On a hit, only `playwright install-deps` runs;
- BuildKit Docker layer caching (`type=gha`, `mode=max`) with dependency-first `Dockerfile.ci` files.

Deviation from PLAN.md: the caches were measured together as one stage, not one PR per cache type. The per-cache
contribution is estimated below from step durations on the same commits.

## Method

Replay round A: 30 commits (5 per category), each pushed once to `exp/a/NN-<category>`. Baseline, cache and optimized
stages ran on every commit, and caches were read from `main`, as for a pull request. One baseline run (commit 23)
failed in `Push images` with a transient GHCR `unknown blob` error after all tests passed. It was re-run (run
40274714179, attempt 2) and the successful attempt is used. Commits 2–20 also carried an extra one-line log file under
`experiments/results/` because of a replay-script bug. No workflow, test selection or Docker build context reads that
path.

## Results (30 paired commits)

Sources: `experiments/results/roundA-30commits-20261026T071508Z/` (export), tables in
[round-a-tables.md](round-a-tables.md), comparison in [round-a-compare-cache.md](round-a-compare-cache.md), step
attribution in [phase-2-step-deltas.md](phase-2-step-deltas.md).

| Metric | Baseline | Cache | Change |
|---|---:|---:|---:|
| Wall-clock p50 | 6m 05s | 5m 14s | −50 s median paired difference, 95% CI [−62, −38] s (−13.8%) |
| Wall-clock p95 | 27m 04s | 6m 35s | tail almost removed |
| Wall-clock mean | 9m 33s | 5m 17s | |
| Billable minutes p50 / mean | 7 / 10.0 | 6 / 5.8 | |
| Cost per 1000 runs (mean × 1000, GitHub-hosted list price) | $59.80 | $34.80 | −42% |

Where the median saving comes from (median per-run seconds, same 30 commits):

| Step group | Baseline | Cache | Paired difference |
|---|---:|---:|---:|
| Docker image build, push and registry login | 84 | 42 | −44 |
| orders-api build and tests (Maven dependencies) | 72 | 60 | −12 |
| Playwright browsers and system packages | 46 | 36 | −10 |
| web `npm ci` | 4 | 2 | −1 |
| analytics `pip install` | 7 | 6 | −1 |
| Toolchain setup (cache restore) | 5 | 9 | +4 |
| Post-job cache save and cleanup | 0 | 8 | +8 |

## Findings

- **Docker layer caching is the largest single saving** (−44 s at the median). It works because `Dockerfile.ci`
  copies dependency manifests before source.
- **Dependency caches are small wins on fast runners.** `npm ci` and `pip install` took only a few seconds even
  without a cache, because GitHub's network to the npm and PyPI registries is fast. Cache restore and save cost back
  about 12 s.
- **The tail matters more than the median.** The cache stage's p95 is 6m 35s against 27m 04s, and the mean cost per
  1000 runs is 42% lower, while the median improves by 13.8%. The slow baseline runs were slow in the browser and
  system-package install step. See the correction in [phase-0-results.md](phase-0-results.md) for what is and is not
  known about why.

## Acceptance criteria (PLAN.md §4 Phase 2)

| Criterion | Status |
|---|---|
| Cache hit rate ≥ 90% on warm runs | **Not computed for this report:** cache-event log parsing for round A was interrupted by the full disk and is being re-run; the step durations above show the caches being used |
| Time saved reported per cache type | **Met, by step attribution** (not by separate PRs; deviation noted) |
| Tag `opt-cache-v1` | **Met** |
