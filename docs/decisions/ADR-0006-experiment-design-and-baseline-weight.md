# ADR-0006: One workflow per optimization stage, and realistic (not padded) baseline weight

**Status:** accepted (deviates from PLAN.md §4: `ci-optimized.yml` "evolving through phases", and the
"baseline p50 ≥ 18 min" acceptance criterion)

## Context
1. PLAN.md had a single `ci-optimized.yml` that changes phase by phase. Then each stage can only be measured
   at the time it exists, on different commits from the other stages, and the final comparison table
   (baseline / +cache / +parallel / +TIA / +ephemeral) cannot be paired across stages.
2. The first real baseline run (run 40208415730) took 4 min 52 s, not ≥ 18 min. GitHub-hosted
   `ubuntu-latest` runners for public repositories have 4 vCPUs, and the RetailOps workload, while realistic in
   structure, is small in absolute size.

## Decision
1. **Stage-per-workflow.** All stages exist at the same time as separate workflow files listening on
   `main` and `exp/**`:

   | Workflow | Stage | Adds |
   |---|---|---|
   | `ci-baseline.yml` | 0 | nothing (frozen at `baseline-v1`) |
   | `ci-cache.yml` | 1 | dependency caches (Maven, npm, pip, Playwright browsers) + Docker layer cache (`type=gha`) with dependency-first `Dockerfile.ci` |
   | `ci-parallel.yml` | 2 | stage 1 + DAG of parallel jobs + duration-balanced sharding (`shardkit`) |
   | `ci-optimized.yml` | 3 | stage 2 + path filtering + test impact analysis (`tia`) |
   | `ci-ephemeral.yml` | 4 | stage 3 on autoscaled ephemeral self-hosted runners (ARC) |

   Every experiment commit is pushed once and every stage runs on it, so all comparisons are paired by commit.
   Each stage runs the same build and test commands as the baseline; only the optimization differs.
2. **Baseline weight.** Before freezing, two stages that enterprise pipelines commonly run were added to the
   baseline (and therefore to every stage): cross-browser end-to-end tests (Chromium, Firefox, WebKit) and
   coverage reports for all three apps. No sleeps, no artificial work. The "≥ 18 min" criterion is replaced by:
   *the baseline contains only realistic stages; its measured p50 is reported as is.* Results are reported both
   as absolute time and as relative reduction, and the dissertation discusses how the absolute savings would
   scale for larger workloads.

## Consequences
- One push triggers up to five workflows. With the free plan's 20 concurrent Linux jobs, the replay script
  pushes one commit at a time and the report separates queue time from execution time.
- Caches are branch-scoped in GitHub Actions: `exp/*` branches read caches saved on `main`, as pull requests do.
  Caches are therefore warmed by a run on `main` before each replay round.
- A smaller absolute baseline makes fixed overheads (job start-up, per-job minute rounding) relatively larger.
  That is a finding, not a flaw: it is exactly the trade-off parallelization has on small pipelines.
