Paired comparison on **30** commits: `ci-cache.yml` (A) vs `ci-optimized.yml` (B).

| Metric | A p50 | A p95 | B p50 | B p95 | Δ p50 (B−A) | 95% CI | Reduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Wall-clock (s) | 314 | 395 | 137 | 192 | -178 | [-238, -156] | 56.4% |
| Time to first job (s) | 3 | 3 | 3 | 3 | 0 | [0, 0] | -0.0% |
| Compute used (job-seconds) | 312 | 392 | 269 | 760 | -42 | [-167, 40] | 13.6% |
| Billable minutes | 6.0 | 7.0 | 8.0 | 21.0 | 2.0 | [0.0, 5.5] | -33.3% |
| Cost per run (USD) | $0.0360 | $0.0420 | $0.0480 | $0.1260 | $0.0120 | [$0.0000, $0.0330] | -33.3% |

CI: paired bootstrap of the median difference, 5000 resamples, fixed seed.
