Source export: `experiments/results/phase0-baseline-10runs-20261025T182227Z` (label `phase0-baseline-10runs`, exported 20261025T182227Z, filters: since=2026-10-25T16:57:00Z, branch=None, failed included=False)

### `ci-baseline.yml` — 10 successful runs

| Metric | Value |
|---|---:|
| Wall-clock p50 | 6m 13s |
| Wall-clock p95 | 39m 03s |
| Wall-clock min / max | 5m 08s / 40m 02s |
| Time to first job p50 | 0m 03s |
| Compute used p50 (job-seconds) | 370 s |
| Billable minutes p50 | 7 |
| Cost per run p50 (GitHub-hosted list price) | $0.042 |
| Cost per 1000 runs (p50 × 1000) | $42.00 |
| Wall-clock mean | 14m 30s |
| Billable minutes mean | 14.9 |
| Cost per 1000 runs (mean × 1000) | $89.40 |
| Overhead share p50 | 20.6% |

**Median step time by category (seconds):**

| Category | p50 (s) | Share of p50 total |
|---|---:|---:|
| test | 194.5 | 52.6% |
| image-build | 67.5 | 18.3% |
| install | 67.0 | 18.1% |
| publish | 21.0 | 5.7% |
| lint | 6.0 | 1.6% |
| build | 5.0 | 1.4% |
| toolchain | 5.0 | 1.4% |
| runner-overhead | 2.5 | 0.7% |
| checkout | 1.0 | 0.3% |

**Slowest steps:**

| Step | Category | n | p50 | p95 |
|---|---|---:|---:|---:|
| orders-api - build and test | test | 10 | 1m 14s | 1m 20s |
| Build images | image-build | 10 | 1m 08s | 1m 13s |
| web - install Playwright browsers | install | 10 | 0m 56s | 33m 46s |
| analytics - tests with coverage | test | 10 | 0m 53s | 0m 56s |
| web - e2e tests (chromium, firefox, webkit) | test | 10 | 0m 48s | 0m 52s |
| web - unit tests with coverage | test | 10 | 0m 22s | 0m 24s |
| Push images | publish | 10 | 0m 19s | 0m 21s |
| analytics - install | install | 10 | 0m 06s | 0m 09s |
| web - lint and typecheck | lint | 10 | 0m 06s | 0m 07s |
| web - build | build | 10 | 0m 05s | 0m 06s |
| Set up Node 20 | toolchain | 10 | 0m 04s | 0m 05s |
| web - install | install | 10 | 0m 04s | 0m 04s |

### Individual runs

| Run | Commit | Wall-clock | Billable min | Cost (USD) | Overhead share |
|---|---|---:|---:|---:|---:|
| 40214161420 | `b17eecf2` | 6m 18s | 7 | 0.042 | 17.8% |
| 40214168033 | `b17eecf2` | 5m 08s | 6 | 0.036 | 20.1% |
| 40214174698 | `b17eecf2` | 37m 50s | 38 | 0.228 | 88.0% |
| 40214181579 | `b17eecf2` | 5m 57s | 6 | 0.036 | 17.1% |
| 40214188835 | `b17eecf2` | 6m 08s | 7 | 0.042 | 21.1% |
| 40217251601 | `b17eecf2` | 5m 37s | 6 | 0.036 | 22.7% |
| 40217259366 | `b17eecf2` | 6m 44s | 7 | 0.042 | 18.7% |
| 40217265054 | `b17eecf2` | 40m 02s | 40 | 0.240 | 87.1% |
| 40217272071 | `b17eecf2` | 25m 22s | 26 | 0.156 | 80.7% |
| 40217279929 | `b17eecf2` | 5m 51s | 6 | 0.036 | 17.0% |
