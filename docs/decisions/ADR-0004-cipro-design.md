# ADR-0004: cipro uses only the standard library and archives raw API data

**Status:** accepted (deviates from PLAN.md §2, which listed httpx/pandas/plotly)

## Context
The profiler must run inside any CI job, on any Wipro client machine, with no dependency installs, and its
results must be reproducible after GitHub's log and run retention expires.

## Decision
- Standard library only (`urllib`, `sqlite3`, `tomllib`, `statistics`-style helpers). Charts are rendered
  client-side by Plotly.js loaded from its CDN in the generated HTML.
- Pricing lives in `pricing.toml` (stdlib `tomllib`) instead of YAML.
- `cipro fetch` writes each run's raw API responses (run, jobs with steps, timing) to
  `experiments/results/raw/<workflow>/<run_id>-<attempt>.json`. These files are the evidence and are committed.
  The SQLite database is a rebuildable cache (`cipro rebuild`) and is not committed.
- Billable minutes are computed from job durations with GitHub's per-job round-up rule rather than relying on
  the run timing endpoint, which reports zero billable time for public repositories.

## Consequences
Anyone can regenerate every metric offline from the committed raw JSON.
