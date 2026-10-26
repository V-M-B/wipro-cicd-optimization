Paired comparison on **30** commits: `ci-baseline.yml` (A) vs `ci-optimized.yml` (B).

| Metric | A p50 | A p95 | B p50 | B p95 | Δ p50 (B−A) | 95% CI | Reduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Wall-clock (s) | 365 | 1,624 | 137 | 192 | -228 | [-291, -204] | 62.5% |
| Time to first job (s) | 2 | 3 | 3 | 3 | 0 | [0, 1] | -20.0% |
| Compute used (job-seconds) | 363 | 1,621 | 269 | 760 | -94 | [-219, -6] | 25.9% |
| Billable minutes | 7.0 | 27.1 | 8.0 | 21.0 | 1.0 | [-1.0, 5.0] | -14.3% |
| Cost per run (USD) | $0.0420 | $0.1626 | $0.0480 | $0.1260 | $0.0060 | [$-0.0060, $0.0300] | -14.3% |

CI: paired bootstrap of the median difference, 5000 resamples, fixed seed.
