# ADR-0007: Ephemeral autoscaled runners with ARC on a local k3d cluster

**Status:** accepted; execution needs the repository owner's explicit go-ahead (a GitHub token is stored in the
local cluster)

## Context
Phase 5 measures ephemeral, autoscaled self-hosted runners against GitHub-hosted runners. The author has no
cloud budget; the laptop has 16 CPUs and ~20 GB RAM available to Docker Desktop.

## Decision
- **Controller:** Actions Runner Controller (ARC) in runner-scale-set mode (`gha-runner-scale-set-controller`
  + `gha-runner-scale-set`), on a single-node k3d cluster. `minRunners: 0`, `maxRunners: 6`, each runner
  pod 2 CPU / 3 GiB, one job per pod (ephemeral). ARC long-polls GitHub, so no inbound connectivity is needed.
- **Warm image:** `infra/runner-image/Dockerfile` bakes in JDK 21, Node 20, Python 3.12, the Maven/npm/pip
  dependencies of the repo, and Playwright browsers with their system packages. `ci-ephemeral.yml` is generated
  from `ci-optimized.yml` and differs only by runner label and by dropping toolchain/browser setup steps.
- **Docker builds:** Docker-in-Docker sidecar (`containerMode: dind`). DinD needs a privileged sidecar; this is
  acceptable on a single-tenant laptop cluster running only the owner's code and is called out as a limitation.
  Kaniko or BuildKit rootless are the hardened alternatives for production.
- **Security on a public repo:** workflows trigger only on `push` and `workflow_dispatch`, never on
  `pull_request`/`pull_request_target`, so fork code cannot reach the self-hosted runners. `ci-ephemeral.yml`
  listens on `exp/**` only and every job is gated on the repository variable `ARC_ENABLED`, so pushes never wait
  on a laptop that is switched off. The GitHub token lives only as a Kubernetes secret in the local cluster.
- **Cost model:** self-hosted jobs cost $0 in GitHub billing in the default scenario and $0.002/min in the
  platform-fee scenario (pricing.toml). Compute cost is modeled from pod CPU-seconds × a cited cloud VM price per
  vCPU-second, because the laptop has no bill. If a cloud VM is used for validation, the user approves spend first.

## Consequences
Laptop runners are not representative of cloud network bandwidth; results report queue time, pod cold-start
and job time separately so that the warm-image effect can be separated from hardware differences.
