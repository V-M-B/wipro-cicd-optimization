# CI/CD Pipeline Performance Optimization

Dissertation project (BITS Pilani WILP, carried out at Wipro): profile a realistic CI pipeline and reduce its
build time and cost with caching, parallelization and sharding, test impact analysis, and ephemeral
autoscaled runners. Every number is measured from the GitHub Actions API and reproducible from this repo.

- Plan and acceptance criteria: [PLAN.md](PLAN.md)
- Working rules: [CLAUDE.md](CLAUDE.md)
- Decisions: [docs/decisions](docs/decisions)
- Results per phase: [docs/phase-results](docs/phase-results)

## Layout

| Path | What |
|---|---|
| `apps/orders-api` | Java 21, Spring Boot 3, Maven, JUnit 5, Testcontainers |
| `apps/web` | React 18, TypeScript, Vite, Vitest, Playwright |
| `apps/analytics` | Python 3.12, FastAPI, pytest |
| `libs/shared-schemas` | JSON Schemas + generator for Java/TS/Python types |
| `tools/cipro` | CI profiler (fetch, report, compare, export) |
| `.github/workflows/ci-baseline.yml` | Frozen "legacy" pipeline (tag `baseline-v1`) |
| `experiments/results` | Raw API JSON and immutable exports |

## Reproduce the numbers

```bash
pip install -e tools/cipro[dev]
cipro rebuild                                   # rebuild SQLite from experiments/results/raw
cipro report --workflow ci-baseline.yml --out docs/dashboard
```

To collect fresh data: `cipro fetch --repo OWNER/REPO --workflow ci-baseline.yml --last 50`.

## Status

See the latest file in `docs/phase-results/`.
