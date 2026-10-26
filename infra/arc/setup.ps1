# Phase 5: local ARC on k3d (PowerShell equivalent of setup.sh).
# Needs docker, k3d, kubectl, helm on PATH and $env:GITHUB_PAT (repo scope). Stored only as a k8s secret.
$ErrorActionPreference = "Stop"
$RepoUrl = if ($env:REPO_URL) { $env:REPO_URL } else { "https://github.com/V-M-B/wipro-cicd-optimization" }
$ArcVersion = if ($env:ARC_VERSION) { $env:ARC_VERSION } else { "0.15.0" }
$Charts = "oci://ghcr.io/actions/actions-runner-controller-charts"
if (-not $env:GITHUB_PAT) { throw "set GITHUB_PAT" }

k3d cluster list retailops-ci 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { k3d cluster create --config infra/arc/k3d-cluster.yaml }
docker image inspect retailops-runner:local 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { docker build -f infra/runner-image/Dockerfile -t retailops-runner:local . }
k3d image import retailops-runner:local -c retailops-ci

helm upgrade --install arc --namespace arc-systems --create-namespace --version $ArcVersion "$Charts/gha-runner-scale-set-controller"
kubectl create namespace arc-runners --dry-run=client -o yaml | kubectl apply -f -
kubectl -n arc-runners create secret generic gh-pat --from-literal=github_token=$env:GITHUB_PAT --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install arc-retailops --namespace arc-runners --version $ArcVersion `
  -f infra/arc/runner-scale-set-values.yaml `
  --set githubConfigUrl=$RepoUrl --set githubConfigSecret=gh-pat "$Charts/gha-runner-scale-set"
kubectl -n arc-runners get autoscalingrunnersets
