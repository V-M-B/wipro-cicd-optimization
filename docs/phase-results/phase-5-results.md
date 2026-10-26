# Phase 5 results — ephemeral autoscaled runners

**Status: not measured.** The infrastructure is built and ready to run. No ephemeral-runner pipeline run was
executed, so no Phase 5 numbers exist and none are reported anywhere in this project. The tag `opt-ephemeral-v1`
was not created.

## Why it was not measured

The author's machine did not have enough free disk space. The C: drive is 322 GB, and the space left over by the
author's own data was too small for Phase 5:

| Need | Approximate size |
|---|---|
| Warm runner image (JDK 21, Maven/npm/pip dependencies, three Playwright browsers with system packages) | ~6.5 GB |
| Second copy of the image inside the k3d node (`k3d image import`) | ~6.5 GB |
| Per-pod Docker-in-Docker storage at run time (Testcontainers images, image builds) | several GB, varies |

During the attempt, C: filled to zero twice: 6 MB free on 2026-10-26 before cleanup, and 0 GB after the image build.
Docker Desktop's storage then failed with read-only and I/O errors, and a background replay process lost writes.
After compacting Docker's disk (40.44 GB → 16.56 GB), 25.7 GB was free. That space was used up again during the image
build, partly by activity outside this project. On the owner's instruction, local Phase 5 was stopped, and the runner
image, its build cache and the k3d cluster were removed.

## What was built and verified

| Item | State | Evidence |
|---|---|---|
| `infra/runner-image/Dockerfile` (runner 2.338.1, Python 3.12, JDK 21, browsers) | Built successfully on 2026-10-26 (BuildKit log ends `naming to docker.io/library/retailops-runner:local`) | Earlier build with runner 2.329.0 checked inside the container: Python 3.12.15, Java 21.0.12.1, browsers in `/opt/ms-playwright`, fastapi importable |
| `infra/arc/k3d-cluster.yaml` | Cluster created twice, node Ready (k3s v1.35.5) | kubectl output in session logs |
| ARC controller 0.15.0 (`gha-runner-scale-set-controller`) | Installed and rolled out | `deployment "arc-gha-rs-controller" successfully rolled out` |
| Token secret `gh-pat` in namespace `arc-runners` | Created from the owner's `gh` token (repo, workflow scopes), with the owner's approval | Removed together with the cluster |
| Runner scale set `arc-retailops` | **Not installed** | Blocked before the image import |
| `.github/workflows/ci-ephemeral.yml` | Generated from `ci-optimized.yml` by `scripts/gen_ephemeral.py`; gated by `vars.ARC_ENABLED` (never set); listens on `exp/e/**` only | Never triggered |

## How to run it (about 15 GB free needed)

```bash
# 1. Build the image, create the cluster, install ARC and the scale set
export GITHUB_PAT=<token with repo scope for this repository>   # or $env:GITHUB_PAT in PowerShell
bash infra/arc/setup.sh                                          # or: powershell -File infra/arc/setup.ps1

# 2. Allow the ephemeral workflow to run, then smoke-test it with a full run
gh variable set ARC_ENABLED --body true
gh workflow run ci-ephemeral.yml --ref main

# 3. Replay round E: the same 30 commits through baseline, hosted optimized, and ephemeral optimized
python scripts/replay.py --label e --base origin/main --workflows ci-baseline.yml ci-optimized.yml ci-ephemeral.yml

# 4. Compare hosted vs ephemeral on the same commits
cipro fetch --repo OWNER/REPO --workflow ci-optimized.yml --workflow ci-ephemeral.yml
cipro compare --a ci-optimized.yml --b ci-ephemeral.yml --branch-glob 'exp/e/*'

# 5. Turn it off again
gh variable delete ARC_ENABLED
k3d cluster delete retailops-ci
```

The cost comparison is ready in `cipro`. Self-hosted jobs are $0 in the default scenario and $0.002/min in the
platform-fee scenario (`pricing.toml`). Compute cost would be modeled from pod CPU-seconds and a cited cloud VM price.

## Lessons recorded for the dissertation

- **Disk is part of the cost of warm images.** A warm image moves download time out of every job and into stored
  bytes, and a local Kubernetes cluster doubles them. Capacity planning for self-hosted runners must include disk, not
  only CPU and memory.
- **Laptop-hosted runners are fragile.** Idle-sleep, a full disk and Docker Desktop restarts each interrupted this
  phase or the replay. That is an argument for running ARC on a managed cluster in a real engagement.

## Acceptance criteria (PLAN.md §4 Phase 5)

| Criterion | Status |
|---|---|
| Paired hosted vs ephemeral comparison on ≥ 15 replay commits | **Not met:** not measured (disk space) |
| Scale-to-zero demonstrated | **Not met:** scale set never installed |
| Tag `opt-ephemeral-v1` | **Not created** |
