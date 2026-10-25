# ADR-0002: Baseline pipeline definition and freeze

**Status:** accepted

## Context
Every optimization is measured against a baseline. If the baseline drifts, before/after numbers are meaningless.

## Decision
`.github/workflows/ci-baseline.yml` is one sequential job on `ubuntu-latest`: set up toolchains without
caching, verify generated schemas, `mvn verify`, `npm ci` + lint + typecheck + unit + build + Playwright,
`pip install` + ruff + pytest, then `docker build` and `docker push` for all three images with no layer cache.
It has `permissions` and `timeout-minutes` for safety but no `concurrency` cancellation, no path filters and no
matrix, because those are optimizations under study. JUnit reports are uploaded as an artifact so that test
durations can be profiled; this costs seconds and is kept identical in every pipeline variant.

After tag `baseline-v1` the file is frozen. Only pure bug fixes are allowed, each recorded in a new ADR.

## Consequences
The baseline is deliberately pessimistic but realistic: many enterprise pipelines look like this.
