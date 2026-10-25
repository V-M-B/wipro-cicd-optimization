# Phase 1 results — profiler (`cipro`) and baseline profile

**Status:** complete.

## Tool

`tools/cipro`: standard-library-only Python CLI (ADR-0004). Commands: `fetch`, `logs`, `summary`, `report`,
`compare`, `export`, `rebuild`. Raw API responses are archived per run in `experiments/results/raw/` and are the
evidence; the SQLite database is a rebuildable cache.

| Check | Result |
|---|---|
| Unit tests | 52 passing, 96% statement coverage (`cd tools/cipro && pytest --cov=cipro`) |
| Works on an arbitrary public repo | Smoke-tested on `pallets/flask` (`tests.yaml`): fetch, logs, report, summary all ran |
| Cost model sourced | `pricing.toml`: GitHub-hosted per-minute prices from docs.github.com (checked 2026-10-25), per-job round-up rule; self-hosted platform fee shown as a scenario because its status is contested |

Defects found while profiling real logs and fixed: ANSI colour codes hid the Vitest summary line; JUnit per-test
times exclude class set-up, so `shardkit` now uses the suite time when it is larger (Spring context start-up).

## Baseline profile

Dashboard: `docs/dashboard/index.html` (regenerate with `cipro report --workflow ci-baseline.yml --since
2026-10-25T16:57:00Z --out docs/dashboard`). Tables: [phase-0-1-baseline-tables.md](phase-0-1-baseline-tables.md).

Waste breakdown of the median run (from the tables): tests 52.6%, image builds 18.3%, dependency/browser
installs 18.1%, image push 5.7%, everything else under 2% each. Overhead share (runner overhead, checkout, cache,
toolchain, installs) p50 = 20.6%; in the three slow runs it was 80.7–88.0%.

The critical path of a single sequential job is the job itself, so the first lever is not parallelism but removing
repeated work (installs, image rebuilds) and, for the tail, the apt dependency.

## Acceptance criteria

| Criterion (PLAN.md §4 Phase 1) | Status |
|---|---|
| Dashboard with waste breakdown from ≥ 10 baseline runs | **Met** (10 runs) |
| Baseline table: p50, p95, billable min/run, cost/run, % time in setup | **Met** (tables file) |
| `cipro` tests ≥ 80% coverage; works on an arbitrary public repo | **Met** (96%; pallets/flask) |
