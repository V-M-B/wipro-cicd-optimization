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

## Addendum (2026-10-26): what changed when it was actually run

- **Runner version:** the image now pins `actions/runner` 2.338.1. The original pin, 2.329.0, was a year old, and
  GitHub stops accepting registrations from runner versions that are too old.
- **No registry:** the runner image is loaded into the cluster with `k3d image import`. This avoids running a
  registry container next to the cluster.
- **Windows kubeconfig:** k3d wrote `host.docker.internal` into the kubeconfig, which resolved to an unreachable LAN
  address. `kubeAPI.host: 127.0.0.1` is pinned in `infra/arc/k3d-cluster.yaml`.
- **Versions:** ARC 0.15.0 (0.15.1 was three days old and was skipped), k3d 5.9.0, Helm 3.22.1, k3s 1.35.5.
  k3d and Helm were downloaded from their release pages and checksum-verified.
- **Disk:** the image is about 6.5 GB, and the k3d import stores a second copy. The author's C: drive filled up during
  the first attempt (6 MB free) and Docker's storage failed. Recovery: the project's images and build cache were
  removed, then Docker's virtual disk was compacted with diskpart (40.44 GB → 16.56 GB). Teams reproducing this need
  about 15 GB free.
- **Credential:** the token in the `gh-pat` secret is the repository owner's `gh` CLI token (scopes: repo, workflow),
  used with the owner's explicit approval. It exists only inside the local cluster, and deleting the cluster removes it.

## Addendum 2 (2026-10-26): not executed locally

On the repository owner's instruction, Phase 5 was not run on the author's laptop because of disk space (see
`docs/phase-results/phase-5-results.md`). The infrastructure stays in the repository, ready to run on a machine or
cluster with about 15 GB free. No Phase 5 numbers are reported.
