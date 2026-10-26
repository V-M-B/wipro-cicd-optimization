Paired comparison on **30** commits: `ci-baseline.yml` (A) vs `ci-cache.yml` (B).

| Metric | A p50 | A p95 | B p50 | B p95 | Δ p50 (B−A) | 95% CI | Reduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Wall-clock (s) | 365 | 1,624 | 314 | 395 | -50 | [-62, -38] | 13.8% |
| Time to first job (s) | 2 | 3 | 3 | 3 | 0 | [0, 1] | -20.0% |
| Compute used (job-seconds) | 363 | 1,621 | 312 | 392 | -52 | [-62, -38] | 14.2% |
| Billable minutes | 7.0 | 27.1 | 6.0 | 7.0 | -1.0 | [-1.0, 0.0] | 14.3% |
| Cost per run (USD) | $0.0420 | $0.1626 | $0.0360 | $0.0420 | $-0.0060 | [$-0.0060, $0.0000] | 14.3% |

CI: paired bootstrap of the median difference, 5000 resamples, fixed seed.
