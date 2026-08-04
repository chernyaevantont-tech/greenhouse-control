#!/usr/bin/env bash
# regen-v2 launcher. Same cluster and conventions as ../cluster/submit.sh, but a separate
# namespace and PVC so no 2026-06/07 partial can reach the merged tables.
#
# Order matters:
#   image -> pvc -> smoke -> (read the smoke gate output) -> main + mech -> merge -> pull
#
# Nothing after `smoke` should be submitted until the smoke job's verify output has been
# read by a human. It is the only cheap chance to catch a broken image or config before
# ~250 CPU-hours are spent.
set -euo pipefail

NS=greenhouse-regen
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S="$HERE/k8s"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

IMAGE_REF="docker.io/agro/greenhouse-regen:v1"        # what the manifests pull
IMAGE_PUSH="localhost:5000/agro/greenhouse-regen:v1"  # where we push on admin-01
ADMIN_WIFI=192.168.1.148
ADMIN_USER=ubuntu

step_image() {
  echo "# Build+push MUST run on admin-01 (internet + local registry)."
  echo "# The regen dir is new, so the old greenhouse-e3:v3 image does NOT contain it."
  set -x
  docker build -f own-article/cluster/Dockerfile -t "$IMAGE_PUSH" "$REPO_ROOT"
  docker push "$IMAGE_PUSH"
  set +x
}

step_pvc()   { kubectl apply -f "$K8S/00-pvc.yaml"; kubectl -n "$NS" get pvc regen-results; }
step_smoke() {
  kubectl apply -f "$K8S/10-smoke.yaml"
  echo "# wait, then READ the gate output before going further:"
  echo "kubectl -n $NS wait --for=condition=complete --timeout=3600s job/regen-smoke"
  echo "kubectl -n $NS logs -l wave=smoke --tail=-1"
}
step_main()    { kubectl apply -f "$K8S/20-main.yaml"; }
step_mech()    { kubectl apply -f "$K8S/30-mechanism-parity.yaml"; }
step_support() { kubectl apply -f "$K8S/40-support.yaml"; }
step_merge() {
  kubectl apply -f "$K8S/90-merge-verify.yaml"
  kubectl -n "$NS" wait --for=condition=complete --timeout=3600s job/regen-merge || true
  kubectl -n "$NS" logs -l wave=merge --tail=-1
}

step_watch() {
  kubectl -n "$NS" get jobs -l app=greenhouse-regen
  kubectl -n "$NS" get pods -l app=greenhouse-regen -o wide | head -30
  cat <<'EOF'
# tail one wave:            kubectl -n greenhouse-regen logs -f -l wave=cheap --prefix --max-log-requests=20
# per-index completion:     kubectl -n greenhouse-regen get job regen-main-cheap -o jsonpath='{.status.completedIndexes}{"\n"}'
EOF
}

step_pull() {
  kubectl -n "$NS" delete pod regen-puller --ignore-not-found
  kubectl -n "$NS" run regen-puller --image="$IMAGE_REF" --restart=Never \
    --overrides='{"spec":{"containers":[{"name":"c","image":"'"$IMAGE_REF"'","command":["sleep","3600"],"volumeMounts":[{"name":"r","mountPath":"/results"}]}],"volumes":[{"name":"r","persistentVolumeClaim":{"claimName":"regen-results"}}]}}'
  kubectl -n "$NS" wait --for=condition=Ready pod/regen-puller --timeout=300s
  mkdir -p "$HERE/results_pull"
  kubectl -n "$NS" cp regen-puller:/results "$HERE/results_pull"
  kubectl -n "$NS" delete pod regen-puller --ignore-not-found
  echo "pulled -> $HERE/results_pull"
  echo "NOW COMMIT IT. The 2026-07 cluster results lived untracked on one laptop for two weeks."
}

case "${1:-}" in
  image) step_image ;;  pvc)  step_pvc ;;   smoke)   step_smoke ;;
  main)  step_main ;;   mech) step_mech ;;  support) step_support ;;
  merge) step_merge ;;  watch) step_watch ;; pull)   step_pull ;;
  all)   step_main; step_mech; step_support; step_watch ;;
  *) echo "usage: bash submit.sh {image|pvc|smoke|main|mech|support|all|merge|watch|pull}"; exit 1 ;;
esac
