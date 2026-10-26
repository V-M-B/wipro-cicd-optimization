#!/usr/bin/env bash
# Phase 5: local ARC on k3d. Needs docker, k3d, kubectl, helm, and a GitHub token with `repo` scope in GITHUB_PAT.
# The token is stored only as a Kubernetes secret in the local cluster.
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/V-M-B/wipro-cicd-optimization}"
: "${GITHUB_PAT:?set GITHUB_PAT}"
ARC_VERSION="${ARC_VERSION:-0.15.0}"
CHARTS=oci://ghcr.io/actions/actions-runner-controller-charts

k3d cluster list retailops-ci >/dev/null 2>&1 || k3d cluster create --config infra/arc/k3d-cluster.yaml
docker image inspect retailops-runner:local >/dev/null 2>&1 || \
  docker build -f infra/runner-image/Dockerfile -t retailops-runner:local .
k3d image import retailops-runner:local -c retailops-ci

helm upgrade --install arc --namespace arc-systems --create-namespace --version "$ARC_VERSION" \
  "$CHARTS/gha-runner-scale-set-controller"

kubectl create namespace arc-runners --dry-run=client -o yaml | kubectl apply -f -
kubectl -n arc-runners create secret generic gh-pat --from-literal=github_token="$GITHUB_PAT" \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install arc-retailops --namespace arc-runners --version "$ARC_VERSION" \
  -f infra/arc/runner-scale-set-values.yaml \
  --set githubConfigUrl="$REPO_URL" --set githubConfigSecret=gh-pat \
  "$CHARTS/gha-runner-scale-set"
kubectl -n arc-runners get autoscalingrunnersets
