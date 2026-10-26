Median per-run seconds on 30 paired commits (`exp/a/*`). Source: `experiments/results/step-deltas-ci-baseline-vs-ci-cache-20261026T073810Z.json`

| Step group | `ci-baseline.yml` p50 (s) | `ci-cache.yml` p50 (s) | Median paired difference (s) |
|---|---:|---:|---:|
| Toolchain setup (Java/Node/Python) | 5 | 9 | +4 |
| orders-api build and tests (Maven dependencies) | 72 | 60 | -12 |
| web npm ci | 4 | 2 | -1 |
| Playwright browsers and system packages | 46 | 36 | -10 |
| analytics pip install | 7 | 6 | -1 |
| Docker image build, push and registry login | 84 | 42 | -44 |
| Post-job cache save and cleanup | 0 | 8 | +8 |
