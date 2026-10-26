Source export: `experiments/results/roundA-30commits-20261026T071508Z` (label `roundA-30commits`, exported 20261026T071508Z, filters: since=None, branch=exp/a/*, failed included=False)

### `ci-baseline.yml` — 30 successful runs

| Metric | Value |
|---|---:|
| Wall-clock p50 | 6m 05s |
| Wall-clock p95 | 27m 04s |
| Wall-clock min / max | 4m 59s / 36m 47s |
| Time to first job p50 | 0m 02s |
| Compute used p50 (job-seconds) | 363 s |
| Billable minutes p50 | 7 |
| Cost per run p50 (GitHub-hosted list price) | $0.042 |
| Cost per 1000 runs (p50 × 1000) | $42.00 |
| Wall-clock mean | 9m 33s |
| Billable minutes mean | 10.0 |
| Cost per 1000 runs (mean × 1000) | $59.80 |
| Overhead share p50 | 19.1% |

**Median step time by category (seconds):**

| Category | p50 (s) | Share of p50 total |
|---|---:|---:|
| test | 192.5 | 54.5% |
| image-build | 64.5 | 18.2% |
| install | 58.5 | 16.5% |
| publish | 19.0 | 5.4% |
| lint | 6.0 | 1.7% |
| build | 5.0 | 1.4% |
| toolchain | 5.0 | 1.4% |
| runner-overhead | 2.0 | 0.6% |
| checkout | 1.0 | 0.3% |

**Slowest steps:**

| Step | Category | n | p50 | p95 |
|---|---|---:|---:|---:|
| orders-api - build and test | test | 30 | 1m 12s | 1m 18s |
| Build images | image-build | 30 | 1m 04s | 1m 12s |
| analytics - tests with coverage | test | 30 | 0m 52s | 0m 55s |
| web - e2e tests (chromium, firefox, webkit) | test | 30 | 0m 48s | 0m 53s |
| web - install Playwright browsers | install | 30 | 0m 46s | 22m 05s |
| web - unit tests with coverage | test | 30 | 0m 22s | 0m 24s |
| Push images | publish | 30 | 0m 17s | 0m 22s |
| analytics - install | install | 30 | 0m 07s | 0m 12s |
| web - lint and typecheck | lint | 30 | 0m 06s | 0m 07s |
| web - build | build | 30 | 0m 05s | 0m 06s |
| Set up Node 20 | toolchain | 30 | 0m 04s | 0m 05s |
| web - install | install | 30 | 0m 04s | 0m 04s |

### `ci-cache.yml` — 30 successful runs

| Metric | Value |
|---|---:|
| Wall-clock p50 | 5m 14s |
| Wall-clock p95 | 6m 35s |
| Wall-clock min / max | 3m 47s / 6m 40s |
| Time to first job p50 | 0m 03s |
| Compute used p50 (job-seconds) | 312 s |
| Billable minutes p50 | 6 |
| Cost per run p50 (GitHub-hosted list price) | $0.036 |
| Cost per 1000 runs (p50 × 1000) | $36.00 |
| Wall-clock mean | 5m 17s |
| Billable minutes mean | 5.8 |
| Cost per 1000 runs (mean × 1000) | $34.80 |
| Overhead share p50 | 26.1% |

**Median step time by category (seconds):**

| Category | p50 (s) | Share of p50 total |
|---|---:|---:|
| test | 184.0 | 60.0% |
| install | 39.5 | 12.9% |
| publish | 38.5 | 12.6% |
| cache | 15.5 | 5.1% |
| runner-overhead | 11.0 | 3.6% |
| lint | 6.0 | 2.0% |
| build | 5.0 | 1.6% |
| toolchain | 5.0 | 1.6% |
| checkout | 1.0 | 0.3% |
| image-build | 1.0 | 0.3% |

**Slowest steps:**

| Step | Category | n | p50 | p95 |
|---|---|---:|---:|---:|
| orders-api - build and test | test | 30 | 0m 60s | 1m 11s |
| analytics - tests with coverage | test | 30 | 0m 54s | 0m 56s |
| web - e2e tests (chromium, firefox, webkit) | test | 30 | 0m 48s | 0m 59s |
| web - install Playwright system dependencies | install | 30 | 0m 31s | 0m 59s |
| web - unit tests with coverage | test | 30 | 0m 22s | 0m 24s |
| Set up Node 20 (with npm cache) | cache | 30 | 0m 06s | 0m 09s |
| web - lint and typecheck | lint | 30 | 0m 06s | 0m 08s |
| analytics - install | install | 30 | 0m 06s | 0m 10s |
| Build and push image orders-api | publish | 30 | 0m 06s | 0m 45s |
| Build and push image web | publish | 30 | 0m 06s | 0m 37s |
| web - build | build | 30 | 0m 05s | 0m 06s |
| web - restore Playwright browsers cache | cache | 30 | 0m 05s | 0m 09s |

### `ci-optimized.yml` — 30 successful runs

| Metric | Value |
|---|---:|
| Wall-clock p50 | 2m 17s |
| Wall-clock p95 | 3m 12s |
| Wall-clock min / max | 0m 08s / 9m 34s |
| Time to first job p50 | 0m 03s |
| Compute used p50 (job-seconds) | 269 s |
| Billable minutes p50 | 8 |
| Cost per run p50 (GitHub-hosted list price) | $0.048 |
| Cost per 1000 runs (p50 × 1000) | $48.00 |
| Wall-clock mean | 2m 08s |
| Billable minutes mean | 9.6 |
| Cost per 1000 runs (mean × 1000) | $57.80 |
| Overhead share p50 | 51.8% |

**Median step time by category (seconds):**

| Category | p50 (s) | Share of p50 total |
|---|---:|---:|
| cache | 76.0 | 31.4% |
| test | 67.0 | 27.7% |
| runner-overhead | 23.0 | 9.5% |
| install | 18.0 | 7.4% |
| image-build | 17.0 | 7.0% |
| other | 16.5 | 6.8% |
| lint | 8.0 | 3.3% |
| checkout | 6.0 | 2.5% |
| publish | 5.5 | 2.3% |
| build | 5.0 | 2.1% |

**Slowest steps:**

| Step | Category | n | p50 | p95 |
|---|---|---:|---:|---:|
| orders-api - integration tests (shard 1) | test | 12 | 0m 45s | 0m 48s |
| Build image orders-api (cache warm-up, no push) | cache | 12 | 0m 38s | 1m 11s |
| Push orders-api (from cache) | cache | 12 | 0m 36s | 0m 58s |
| Push web (from cache) | cache | 12 | 0m 32s | 0m 40s |
| orders-api - integration tests (shard 0) | test | 12 | 0m 30s | 0m 36s |
| Build image web (cache warm-up, no push) | cache | 12 | 0m 30s | 0m 43s |
| Install Playwright system dependencies | install | 12 | 0m 28s | 3m 52s |
| analytics - tests with coverage (shard 1) | test | 10 | 0m 23s | 0m 31s |
| analytics - tests with coverage (shard 0) | test | 11 | 0m 22s | 0m 34s |
| web - selected e2e tests (firefox) | test | 12 | 0m 20s | 0m 23s |
| Install Playwright system dependencies | install | 12 | 0m 20s | 0m 36s |
| web - selected e2e tests (webkit) | test | 12 | 0m 20s | 0m 23s |

### Individual runs

| Run | Commit | Wall-clock | Billable min | Cost (USD) | Overhead share |
|---|---|---:|---:|---:|---:|
| 40221382787 | `928b3448` | 6m 30s | 7 | 0.042 | 19.2% |
| 40221943452 | `c767365c` | 4m 59s | 5 | 0.030 | 19.4% |
| 40222368553 | `995ecf94` | 5m 52s | 6 | 0.036 | 16.7% |
| 40222858104 | `8ae325b0` | 6m 19s | 7 | 0.042 | 19.6% |
| 40223410227 | `4b9a3b2c` | 6m 14s | 7 | 0.042 | 20.2% |
| 40223949756 | `43a86a9b` | 5m 58s | 6 | 0.036 | 17.2% |
| 40224458267 | `f737e44d` | 5m 42s | 6 | 0.036 | 19.0% |
| 40224955940 | `3fd0fec7` | 6m 00s | 6 | 0.036 | 17.5% |
| 40225454777 | `ee1e52fe` | 5m 19s | 6 | 0.036 | 18.9% |
| 40225890567 | `d3b43830` | 6m 02s | 6 | 0.036 | 18.2% |
| 40226373518 | `6696b54d` | 27m 55s | 28 | 0.168 | 82.6% |
| 40228586539 | `f5022ba6` | 6m 07s | 7 | 0.042 | 18.8% |
| 40229150892 | `42a51b86` | 5m 23s | 6 | 0.036 | 20.5% |
| 40229642124 | `54639072` | 12m 51s | 13 | 0.078 | 66.8% |
| 40230670274 | `7b4d5907` | 26m 01s | 26 | 0.156 | 83.5% |
| 40232764235 | `f3541162` | 6m 08s | 7 | 0.042 | 17.9% |
| 40233283547 | `dc41592c` | 6m 03s | 7 | 0.042 | 22.9% |
| 40233789858 | `5b142012` | 20m 08s | 21 | 0.126 | 76.7% |
| 40235442264 | `dd6a59f7` | 36m 47s | 37 | 0.222 | 87.7% |
| 40238346314 | `962e179f` | 21m 00s | 21 | 0.126 | 78.3% |
| 40273531402 | `4a87f881` | 5m 38s | 6 | 0.036 | 17.4% |
| 40274082282 | `8d0922b6` | 5m 34s | 6 | 0.036 | 17.0% |
| 40274714179 | `ad75609a` | 6m 16s | 7 | 0.042 | 20.7% |
| 40275269244 | `33ea69d4` | 6m 15s | 7 | 0.042 | 18.9% |
| 40279474944 | `476943cd` | 6m 25s | 7 | 0.042 | 21.6% |
| 40280145807 | `3625b88e` | 5m 07s | 6 | 0.036 | 19.9% |
| 40280695449 | `a0f2e3f3` | 5m 57s | 6 | 0.036 | 17.1% |
| 40281296140 | `546b858d` | 5m 42s | 6 | 0.036 | 17.0% |
| 40281896092 | `67f3223f` | 6m 08s | 7 | 0.042 | 17.7% |
| 40282577672 | `a0131eea` | 6m 02s | 6 | 0.036 | 16.8% |
| 40221382766 | `928b3448` | 6m 06s | 7 | 0.042 | 33.8% |
| 40221943488 | `c767365c` | 5m 09s | 6 | 0.036 | 26.6% |
| 40222368556 | `995ecf94` | 3m 47s | 4 | 0.024 | 28.1% |
| 40222858111 | `8ae325b0` | 6m 40s | 7 | 0.042 | 22.6% |
| 40223410189 | `4b9a3b2c` | 5m 14s | 6 | 0.036 | 29.4% |
| 40223949818 | `43a86a9b` | 5m 26s | 6 | 0.036 | 23.4% |
| 40224458455 | `f737e44d` | 5m 14s | 6 | 0.036 | 23.6% |
| 40224955880 | `3fd0fec7` | 5m 07s | 6 | 0.036 | 20.2% |
| 40225454665 | `ee1e52fe` | 4m 56s | 5 | 0.030 | 24.8% |
| 40225890590 | `d3b43830` | 5m 43s | 6 | 0.036 | 19.9% |
| 40226373557 | `6696b54d` | 6m 31s | 7 | 0.042 | 46.4% |
| 40228586589 | `f5022ba6` | 5m 43s | 6 | 0.036 | 21.8% |
| 40229150857 | `42a51b86` | 5m 01s | 5 | 0.030 | 20.9% |
| 40229642218 | `54639072` | 4m 30s | 5 | 0.030 | 28.4% |
| 40230670278 | `7b4d5907` | 5m 29s | 6 | 0.036 | 32.1% |
| 40232764284 | `f3541162` | 5m 48s | 6 | 0.036 | 20.7% |
| 40233283744 | `dc41592c` | 4m 19s | 5 | 0.030 | 27.8% |
| 40233789883 | `5b142012` | 5m 23s | 6 | 0.036 | 24.6% |
| 40235443086 | `dd6a59f7` | 4m 15s | 5 | 0.030 | 26.1% |
| 40238346326 | `962e179f` | 4m 58s | 5 | 0.030 | 20.2% |
| 40273531390 | `4a87f881` | 4m 28s | 5 | 0.030 | 28.1% |
| 40274082285 | `8d0922b6` | 6m 38s | 7 | 0.042 | 27.9% |
| 40274714173 | `ad75609a` | 5m 23s | 6 | 0.036 | 29.0% |
| 40275269334 | `33ea69d4` | 5m 22s | 6 | 0.036 | 32.0% |
| 40279474964 | `476943cd` | 5m 23s | 6 | 0.036 | 26.2% |
| 40280145683 | `3625b88e` | 5m 05s | 6 | 0.036 | 19.3% |
| 40280695366 | `a0f2e3f3` | 5m 15s | 6 | 0.036 | 26.4% |
| 40281296130 | `546b858d` | 5m 39s | 6 | 0.036 | 19.4% |
| 40281896122 | `67f3223f` | 5m 05s | 6 | 0.036 | 21.3% |
| 40282577683 | `a0131eea` | 4m 53s | 5 | 0.030 | 33.3% |
| 40221382790 | `928b3448` | 2m 36s | 11 | 0.066 | 57.4% |
| 40221943447 | `c767365c` | 2m 54s | 9 | 0.054 | 50.2% |
| 40222368544 | `995ecf94` | 0m 57s | 5 | 0.030 | 54.5% |
| 40222858087 | `8ae325b0` | 2m 48s | 21 | 0.126 | 51.4% |
| 40223410244 | `4b9a3b2c` | 0m 08s | 1 | 0.006 | 66.7% |
| 40223949891 | `43a86a9b` | 2m 01s | 8 | 0.048 | 39.9% |
| 40224458312 | `f737e44d` | 2m 45s | 11 | 0.066 | 60.6% |
| 40224955947 | `3fd0fec7` | 2m 15s | 7 | 0.042 | 39.3% |
| 40225454663 | `ee1e52fe` | 1m 09s | 6 | 0.036 | 42.6% |
| 40225890596 | `d3b43830` | 2m 41s | 21 | 0.126 | 47.2% |
| 40226373498 | `6696b54d` | 0m 08s | 1 | 0.006 | 66.7% |
| 40228586579 | `f5022ba6` | 2m 42s | 13 | 0.078 | 56.2% |
| 40229150899 | `42a51b86` | 2m 19s | 12 | 0.072 | 62.9% |
| 40229642294 | `54639072` | 2m 56s | 8 | 0.048 | 52.8% |
| 40230670304 | `7b4d5907` | 1m 07s | 6 | 0.036 | 44.1% |
| 40232764194 | `f3541162` | 3m 09s | 23 | 0.138 | 51.6% |
| 40233283577 | `dc41592c` | 0m 08s | 1 | 0.006 | 66.7% |
| 40233789964 | `5b142012` | 2m 34s | 12 | 0.072 | 62.4% |
| 40235442271 | `dd6a59f7` | 9m 34s | 18 | 0.108 | 82.2% |
| 40238346298 | `962e179f` | 2m 09s | 7 | 0.042 | 42.9% |
| 40273531384 | `4a87f881` | 0m 59s | 6 | 0.036 | 52.0% |
| 40274082225 | `8d0922b6` | 2m 38s | 20 | 0.120 | 47.7% |
| 40274714188 | `ad75609a` | 0m 35s | 2 | 0.012 | 34.6% |
| 40275269406 | `33ea69d4` | 1m 25s | 6 | 0.036 | 30.1% |
| 40279474973 | `476943cd` | 3m 04s | 12 | 0.072 | 62.8% |
| 40280145586 | `3625b88e` | 2m 25s | 8 | 0.048 | 46.6% |
| 40280695308 | `a0f2e3f3` | 1m 09s | 6 | 0.036 | 37.6% |
| 40281296126 | `546b858d` | 3m 14s | 21 | 0.126 | 52.4% |
| 40281896082 | `67f3223f` | 0m 11s | 1 | 0.006 | 75.0% |
| 40282577702 | `a0131eea` | 1m 25s | 6 | 0.036 | 21.9% |
