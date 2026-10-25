# cipro — CI profiler for GitHub Actions

`cipro` pulls workflow runs, jobs and steps from the GitHub REST API into SQLite, archives the raw API
responses, and turns them into metrics: wall-clock, queue time, billable minutes, modeled cost, a waste
breakdown by step category, a heuristic critical path, and paired before/after comparisons with bootstrap
confidence intervals. It uses only the Python standard library.

## Install

```bash
pip install -e tools/cipro[dev]
```

Authentication: `GITHUB_TOKEN` or `GH_TOKEN`, otherwise the token from `gh auth token`.

## Commands

```bash
# Pull completed runs of one or more workflows (raw JSON archived per run in experiments/results/raw/)
cipro fetch --repo OWNER/REPO --workflow ci-baseline.yml --workflow ci-optimized.yml --last 100

# Download job logs and extract cache hits/misses, Docker layer cache use and test counts
cipro logs --repo OWNER/REPO --workflow ci-baseline.yml

# Metrics as JSON
cipro summary --workflow ci-baseline.yml

# Paired comparison on the same commits (only exp/* branches), Markdown table for PR descriptions
cipro compare --a ci-baseline.yml --b ci-optimized.yml --branch-glob 'exp/*' --json out.json

# Static HTML dashboard (Plotly)
cipro report --workflow ci-baseline.yml --workflow ci-optimized.yml --pair ci-baseline.yml:ci-optimized.yml --out docs/dashboard

# Immutable, timestamped CSV/JSON export for the dissertation
cipro export --workflow ci-baseline.yml --label phase0-baseline

# Rebuild the database offline from archived raw JSON
cipro rebuild
```

Global option `--db` (default `experiments/results/cipro.sqlite`). Filters on `summary`, `report`,
`compare`, `export`: `--branch-glob`, `--since`, `--include-failed` (default: successful runs only).

## Metric definitions

| Metric | Definition |
|---|---|
| Wall-clock | First job `created_at` to last job `completed_at`. Includes queueing. |
| Execution span | First job `started_at` to last job `completed_at`. |
| Time to first job | First job `created_at` to first job `started_at`. |
| Queue total | Sum over executed jobs of `started_at − created_at`. |
| Job-seconds | Sum of executed job durations: compute actually consumed. |
| Billable minutes | Sum over executed jobs of `ceil(duration / 60)`, GitHub's per-job rounding rule. Skipped jobs are free. |
| Cost | Billable minutes × per-minute price for the runner label (`pricing.toml`, sourced and dated). Self-hosted jobs cost 0 in the default scenario and the platform-fee price in the `cost_usd_self_hosted_fee` scenario. |
| Overhead share | Step time in runner overhead, checkout, cache, toolchain setup and dependency install ÷ all step time. |
| Critical path | Heuristic: from the last-finishing job, repeatedly step back to the latest-finishing job that completed before the current job started. The API does not expose `needs:` edges. |
| Paired comparison | Runs of two workflows are paired by `head_sha` (latest run per sha). Reported: p50/p95 per side, median difference with a 95% paired bootstrap CI (5000 resamples, fixed seed). |

Step categories are assigned by name in `classify.py` (first matching rule wins).

## Tests

```bash
cd tools/cipro && pytest --cov=cipro
```

51 tests, 96% statement coverage at the time of writing. Smoke-tested against `pallets/flask` (`tests.yaml`).
