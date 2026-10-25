# Working rules for the agent building this project

Read `PLAN.md` first. It fixes the technology choices, repository layout, phases and acceptance criteria. These rules govern *how* you work.

## Integrity of measurements (most important)
- Never fabricate, estimate, or "round to plausible" a metric. Every number in any results file, PR description, or report must come from a file under `experiments/results/` produced by `cipro` or a documented script.
- If something could not be measured, write "not measured" and why. Do not fill the gap.
- Raw result files are append-only. Never edit them by hand. Re-run the collection instead.
- Prices in `tools/cipro/src/cipro/pricing.toml` must carry a source URL and the date you checked it.
- Report failures honestly: if a workflow is red, a test flaky, or an acceptance criterion missed, say so in the phase results and in your message to the user.

## Experiment hygiene
- `.github/workflows/ci-baseline.yml` is frozen after tag `baseline-v1`. Any change needs an ADR and must be a pure bug fix.
- One optimization per PR. The PR description contains the `cipro compare` before/after table for that change alone.
- Paired comparisons only: compare pipelines on the same commits, never baseline-on-Monday vs optimized-on-Friday.
- Tag the repo at the end of every phase (`baseline-v1`, `opt-cache-v1`, `opt-parallel-v1`, `opt-tia-v1`, `opt-ephemeral-v1`, `experiment-v1`).

## Documentation discipline
- `docs/phase-results/phase-N-results.md` after every phase: commands run, raw file paths, metrics table, chart, open issues.
- `docs/decisions/ADR-xxxx.md` for any decision not already fixed in `PLAN.md` (short: context, decision, consequences).
- `README.md` must always let a reader reproduce every published number from a clean clone.
- Keep `PLAN.md` as the source of truth; if you must deviate, edit the plan and say why in an ADR.

## Safety and cost
- Ask the user before any action that costs money (cloud VMs, paid runners) or needs their credentials (`gh auth login`, cloud logins). Do not try to work around missing credentials.
- Self-hosted/ephemeral runners run only on `push` events from the repository owner. Never let fork pull requests execute on self-hosted runners.
- Never commit secrets. Use GitHub Actions secrets and `GITHUB_TOKEN` with least privilege (`permissions:` block in every workflow).

## Engineering conventions
- Host is Windows 11 with Docker Desktop (WSL2). Prefer cross-platform scripts (Python) over shell-specific ones; where a shell script is needed provide both `.ps1` and `.sh`.
- Python tools (`cipro`, `tia`, `shardkit`) are proper packages under `tools/` with `pyproject.toml`, type hints, `pytest` tests (target ≥ 80% coverage), and a `README.md` with usage examples.
- Generated tests must be real, deterministic, and exercise real code. Record how many were generated and from which templates.
- Workflows: set `permissions:`, `timeout-minutes`, and `concurrency` on every job. Pin third-party actions to a major version at minimum.
- Commit small and often with clear messages. Do not rewrite history on `main`.

## Communication
- At the end of each phase, report: what is done, what is not, what could not be verified, and the exact acceptance criteria status (met / not met with the measured value).
- Do not ask the user questions you can answer by reading `PLAN.md`, the code, or the GitHub API.
