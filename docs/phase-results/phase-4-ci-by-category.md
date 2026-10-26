Paired by commit, round a: `ci-baseline.yml` vs `ci-optimized.yml`. Source: `experiments/results/tia-ci-a-20261026T081157Z.json`

| Category | Commits | Tests executed (median share of baseline) | Wall p50 baseline | Wall p50 stage | Jobs (median) | Billable min p50 baseline → stage |
|---|---:|---:|---:|---:|---:|---:|
| analytics | 5 (5 with logs) | 9% | 5m 52s | 1m 07s | 6 | 6 → 6 |
| backend | 5 (5 with logs) | 5% | 6m 00s | 2m 25s | 7 | 6 → 8 |
| config | 5 (5 with logs) | 33% | 6m 07s | 2m 01s | 7 | 7 → 8 |
| docs | 5 (5 with logs) | 0% | 6m 14s | 0m 08s | 1 | 7 → 1 |
| frontend | 5 (5 with logs) | 11% | 6m 25s | 2m 45s | 9 | 7 → 12 |
| shared-lib | 5 (5 with logs) | 70% | 6m 02s | 2m 48s | 19 | 6 → 21 |
