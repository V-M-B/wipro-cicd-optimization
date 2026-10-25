#!/usr/bin/env bash
# Phase 5: local ARC on k3d. Needs: docker, k3d, kubectl, helm, and a GitHub token with `repo` scope
# for a PUBLIC repo you own, in GITHUB_PAT. The token is stored only as a Kubernetes secret in the local cluster.
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/V-M-B/wipro-cicd-optimization}"
: "${GITHUB_PAT:?set GITHUB_PAT}"
ARC_VERSION="${ARC_VERSION:-0.13.0}"

k3d cluster create --config infra/arc/k3d-cluster.yaml || true
docker build -f infra/runner-image/Dockerfile -t localhost:5050/retailops-runner:latest .
docker push localhost:5050/retailops-runner:latest

helm upgrade --install arc --namespace arc-systems --create-namespace \
  --version "$ARC_VERSION" oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller

kubectl create namespace arc-runners --dry-run=client -o yaml | kubectl apply -f -
kubectl -n arc-runners create secret generic gh-pat --from-literal=github_token="$GITHUB_PAT" \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install arc-retailops --namespace arc-runners --version "$ARC_VERSION" \
  -f infra/arc/runner-scale-set-values.yaml \
  --set githubConfigUrl="$REPO_URL" --set githubConfigSecret=gh-pat \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set
kubectl -n arc-runners get autoscalingrunnersets
