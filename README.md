# CI/CD Pipeline Performance Optimization

Dissertation project (BITS Pilani WILP, carried out at Wipro). It profiles a realistic CI pipeline, then reduces its
build time and cost with caching, parallelization and duration-balanced sharding, and test impact analysis. Every
technique is measured against a frozen baseline on the same commits. An ephemeral-runner stage is built but was not
measured (see [Phase 5](docs/phase-results/phase-5-results.md)).

Every number in this repository is computed from GitHub Actions API data archived in `experiments/results/raw/`.
None was typed by hand.

## Results at a glance

Replay round A: 30 realistic commits in six change categories, run through the baseline and each stage. Medians of
paired runs, from [round-a-tables.md](docs/phase-results/round-a-tables.md) and
[round-a-compare-cache.md](docs/phase-results/round-a-compare-cache.md).

| Stage | Wall-clock p50 | Wall-clock p95 | Billable min p50 | Cost / 1000 runs (mean) |
|---|---:|---:|---:|---:|
| Baseline (frozen, `baseline-v1`) | 6m 05s | 27m 04s | 7 | $59.80 |
| + caching (`ci-cache.yml`) | 5m 14s | 6m 35s | 6 | $34.80 |
| + parallel jobs + sharding + test impact analysis (`ci-optimized.yml`) | 2m 17s | 3m 12s | 8 | $57.80 |

The parallel-only stage (`ci-parallel.yml`) is measured in replay round B. Test impact analysis caught 47 of 47
injected faults that the full suites catch ([Phase 4](docs/phase-results/phase-4-tia-safety.md)).

## Where things are

| Path | What |
|---|---|
| `apps/orders-api` | Java 21, Spring Boot 3.5, Maven, JUnit 5, Testcontainers (375 unit + 45 integration tests) |
| `apps/web` | React 18, TypeScript, Vite 7, Vitest, Playwright (728 unit + 35 e2e tests × 3 browsers) |
| `apps/analytics` | Python 3.12, FastAPI, pytest (615 tests) |
| `libs/shared-schemas` | JSON Schemas + generator for Java/TS/Python types |
| `tools/cipro` | CI profiler: fetch, logs, summary, report, compare, export, rebuild |
| `tools/shardkit` | Duration-balanced test sharding from JUnit XML |
| `tools/tia` | Test impact analysis: static graphs + coverage maps + safety rules |
| `.github/workflows/ci-*.yml` | One workflow per stage (ADR-0006); `nightly-full.yml` builds coverage maps |
| `infra/` | Warm runner image and ARC on k3d (Phase 5, ready to run) |
| `experiments/commits` | The 30 replay patches and manifest |
| `experiments/faults` | The 60 injected faults (seed 7) |
| `experiments/results` | Raw API JSON (`raw/`), immutable exports, comparison and study outputs |
| `docs/phase-results` | Results per phase, with the commands that produced them |
| `docs/decisions` | ADR-0001 … ADR-0007 |
| `docs/playbook` | Porting each technique to Jenkins, Azure DevOps and GitLab CI |
| `docs/dissertation` | Outline (BITS template), figures |

## Reproduce the numbers

```bash
pip install -e tools/cipro -e tools/shardkit -e tools/tia

# 1. Rebuild the database from the archived raw API JSON (offline)
cipro rebuild

# 2. Baseline (Phase 0/1)
cipro export --workflow ci-baseline.yml --label phase0-baseline-10runs --since 2026-10-25T16:57:00Z
python scripts/report_export.py experiments/results/<the new export directory>

# 3. Replay round A comparisons (Phases 2 and 4)
cipro compare --a ci-baseline.yml --b ci-cache.yml --branch-glob 'exp/a/*'
cipro compare --a ci-baseline.yml --b ci-optimized.yml --branch-glob 'exp/a/*'
python scripts/report_step_deltas.py --a ci-baseline.yml --b ci-cache.yml --branch-glob 'exp/a/*'

# 4. Test impact analysis safety study (local; needs JDK 21, Node 20+, Python 3.12, Docker)
python scripts/eval_tia_faults.py
python scripts/report_faults.py experiments/results/tia-faults-20261025T183611Z.json

# 5. Figures and dashboard
python scripts/make_figures.py
cipro report --workflow ci-baseline.yml --workflow ci-cache.yml --workflow ci-parallel.yml --workflow ci-optimized.yml \
  --branch-glob 'exp/*' --out docs/dashboard
```

To collect fresh data on your own fork: push, then run `python scripts/replay.py --label a --workflows
ci-baseline.yml ci-cache.yml ci-optimized.yml` and `cipro fetch --repo OWNER/REPO --workflow ...`.

## Status

| Phase | Status | Results |
|---|---|---|
| 0 Workload and baseline | Done (`baseline-v1`) | [phase-0-results.md](docs/phase-results/phase-0-results.md) |
| 1 Profiler | Done | [phase-1-results.md](docs/phase-results/phase-1-results.md) |
| 2 Caching | Done (`opt-cache-v1`) | [phase-2-results.md](docs/phase-results/phase-2-results.md) |
| 3 Parallelization and sharding | Replay round B running | — |
| 4 Test impact analysis | Safety study done; CI results in progress | [phase-4-tia-safety.md](docs/phase-results/phase-4-tia-safety.md) |
| 5 Ephemeral runners | Not measured (disk space); infrastructure ready | [phase-5-results.md](docs/phase-results/phase-5-results.md) |
| 6 Experiment and analysis | In progress | figures in `docs/dissertation/figures` |
| 7 Playbook and dissertation | Playbook and outline done | [docs/playbook](docs/playbook), [outline.docx](docs/dissertation/outline.docx) |
