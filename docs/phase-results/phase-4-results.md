# Phase 4 results — test impact analysis (`ci-optimized.yml`)

**Status:** complete. Tag `opt-tia-v1` = `6000c9e`, the base of replay round A. Part 1 (safety, fault injection) is in
[phase-4-tia-safety.md](phase-4-tia-safety.md). This file is part 2: what the stage does in CI.

`ci-optimized.yml` = caches + parallel DAG + duration-balanced shards (as in `ci-parallel.yml`) + a `select` job
that runs `scripts/ci_select.py` (tia) and gates every other job. On `main` every suite runs (safety net); on `exp/**`
only impacted tests run and only impacted images are rebuilt.

## Results (replay round A, 30 paired commits)

Sources: [round-a-compare-optimized.md](round-a-compare-optimized.md), per-category table
[phase-4-ci-by-category.md](phase-4-ci-by-category.md) from
`python scripts/report_tia_ci.py --round a --b ci-optimized.yml` → `experiments/results/tia-ci-a-20261026T081157Z.json`.

**Overall vs baseline** (`cipro compare --a ci-baseline.yml --b ci-optimized.yml --branch-glob 'exp/a/*'`):

| Metric | Baseline p50 | TIA stage p50 | Median paired difference | 95% CI |
|---|---:|---:|---:|---:|
| Wall-clock | 365 s | 137 s | −228 s (−62.5%) | [−291, −204] s |
| Compute used (job-seconds) | 363 | 269 | −94 | [−219, −6] |
| Billable minutes | 7 | 8 | +1 | [−1, +5] |

**By change category** (baseline runs all 1,868 tests on every commit):

| Category | Tests executed (median share of baseline) | Wall p50 baseline → TIA | Jobs (median) | Billable min p50 baseline → TIA |
|---|---:|---:|---:|---:|
| docs | 0% | 6m 14s → 0m 08s | 1 | 7 → 1 |
| backend | 5% | 6m 00s → 2m 25s | 7 | 6 → 8 |
| analytics | 9% | 5m 52s → 1m 07s | 6 | 6 → 6 |
| frontend | 11% | 6m 25s → 2m 45s | 9 | 7 → 12 |
| config | 33% | 6m 07s → 2m 01s | 7 | 7 → 8 |
| shared-lib | 70% | 6m 02s → 2m 48s | 19 | 6 → 21 |

## Findings

- **Test selection removes most test work for single-area changes** (0–11% of tests for docs, backend, analytics
  and frontend changes). The floors are the safety rules: all 45 Java integration tests on any backend source
  change, and all e2e specs on any web source change.
- **Wall-clock falls in every category; billable minutes do not.** GitHub bills each job rounded up to a whole
  minute. A frontend change now runs about 9 short jobs instead of 1 long one, so it bills 12 minutes against 7. Only
  docs-only and analytics changes are cheaper. A shared-library change runs 19 jobs and bills 21 minutes, 3.5× the
  baseline.
- **Paired with caching alone, the TIA stage is 56.4% faster but bills 33.3% more** at the median
  ([round-a-compare-cache-vs-optimized.md](round-a-compare-cache-vs-optimized.md)). The speed comes from
  parallelism plus selection, and the extra cost comes from parallelism. Round B (parallel without selection) separates
  the two.
- **Recall:** 47 of 47 injected faults that the suites detect were also detected by the selected tests (part 1).

## Acceptance criteria (PLAN.md §4 Phase 4)

| Criterion | Status |
|---|---|
| Median % of tests executed per category on the replay commits | **Met** (table above) |
| Fault-injection recall ≥ 98%, misses explained, rules updated if systematic | **Met** (100% after the fixture-aware hub fix; the earlier miss is documented) |
| Tag `opt-tia-v1` | **Met** |
