#!/usr/bin/env bash
# Launch helper for the E3 cluster jobs on the bare-metal RKE2 cluster.
#
# Replaces the old server0/server1 nohup+scp workflow (own-article/remote_sync.sh):
#   nohup detached job        -> indexed Kubernetes Job (survives, restarts, sharded)
#   scp partials from 2 hosts -> one shared Longhorn RWX PVC every pod writes to
#   local multiprocessing     -> pod-level parallelism across all cluster nodes
#
# Usage:  bash submit.sh <step>
#   kubeconfig   print/do the kubeconfig fetch+rewrite from admin-01 (step 0)
#   image        build the CPU image and push it to the local registry (run ON admin-01)
#   pvc          create the namespace + Longhorn RWX results PVC
#   knockout     apply the knock-out/knock-in Job         (reviewer #1)
#   multiseason  apply the multi-season cheap-controller Job (reviewer #3)
#   oracle       apply the oracle solver-parity Job        (reviewer #6)
#   watch        show job/pod status and how to tail logs by shard index
#   merge        run the in-cluster merge Job (aggregates /results/* -> *_ablation.csv)
#   pull         copy the merged CSVs off the PVC to ./results_pull on this PC
#   all          pvc + knockout + multiseason + oracle
#
# Prereqs: kubectl on PATH with KUBECONFIG pointing at the cluster (see `kubeconfig`).
set -euo pipefail

NS=greenhouse-e3
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S="$HERE/k8s"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"          # greenhouse-control/

# Image: referenced in manifests by its docker.io name so containerd's mirror rewrites it
# to the local registry; pushed to localhost:5000 (docker treats localhost as insecure OK).
IMAGE_REF="docker.io/agro/greenhouse-e3:v3"      # what the manifests pull
IMAGE_PUSH="localhost:5000/agro/greenhouse-e3:v3" # where we push on admin-01

ADMIN_WIFI=192.168.1.148        # admin-01 Wi-Fi IP (API server + registry host)
ADMIN_USER=ubuntu               # ssh user on admin-01 (rke2 nodes provisioned as 'ubuntu')

step_kubeconfig() {
  cat <<EOF
# ── Step 0: get a kubeconfig from admin-01 (run these on THIS PC) ────────────
# rke2 writes a world-readable kubeconfig (write-kubeconfig-mode 0644) whose server is
# https://127.0.0.1:6443; copy it and rewrite the server to admin-01's reachable IP.
ssh ${ADMIN_USER}@${ADMIN_WIFI} 'cat /etc/rancher/rke2/rke2.yaml' > ~/.kube/agro-cluster.yaml
# (if it is not world-readable on your node: ... 'sudo cat /etc/rancher/rke2/rke2.yaml' ...)
sed -i 's#https://127.0.0.1:6443#https://${ADMIN_WIFI}:6443#' ~/.kube/agro-cluster.yaml
export KUBECONFIG=~/.kube/agro-cluster.yaml
kubectl get nodes -o wide      # expect admin-01 + gpu-01..NN Ready
EOF
}

step_image() {
  echo "# Build+push MUST run on admin-01 (has internet + the local registry)."
  echo "# From the repo root on admin-01 (rsync/clone greenhouse-control there first):"
  set -x
  docker build -f own-article/cluster/Dockerfile -t "$IMAGE_PUSH" \
    "$REPO_ROOT"
  # Optional: route pip through in-cluster devpi if reachable from the build host; admin-01
  # has direct Wi-Fi internet so plain PyPI works too (omit the build-args).
  #   --build-arg PIP_INDEX_URL=http://devpi.jupyterhub.svc.cluster.local:3141/root/pypi/+simple/ \
  #   --build-arg PIP_TRUSTED_HOST=devpi.jupyterhub.svc.cluster.local
  docker push "$IMAGE_PUSH"
  set +x
  echo "# Pushed $IMAGE_PUSH ; manifests pull it as $IMAGE_REF (mirror rewrite)."
}

step_pvc()         { kubectl apply -f "$K8S/results-pvc.yaml"; kubectl -n "$NS" get pvc e3-results; }
step_knockout()    { kubectl apply -f "$K8S/e3-knockout-job.yaml"; }
step_multiseason() { kubectl apply -f "$K8S/e3-multiseason-job.yaml"; }
step_oracle()      { kubectl apply -f "$K8S/e3-oracle-parity-job.yaml"; }

step_watch() {
  echo "== jobs =="
  kubectl -n "$NS" get jobs -l app=greenhouse-e3
  echo "== pods =="
  kubectl -n "$NS" get pods -l app=greenhouse-e3 -o wide
  cat <<'EOF'
# Tail every shard of a job (prefixes each line with the pod):
kubectl -n greenhouse-e3 logs -f -l experiment=knockout --prefix --max-log-requests=20
# Logs for ONE shard index (e.g. seed index 3):
kubectl -n greenhouse-e3 logs -l batch.kubernetes.io/job-completion-index=3 --prefix
# Per-index completion status:
kubectl -n greenhouse-e3 get job e3-knockout -o jsonpath='{.status.completedIndexes}{"\n"}'
EOF
}

# In-cluster merge: one short Job mounts the PVC and runs each runner's --merge mode, so the
# aggregation reads all shard partials off the shared volume (no data leaves the cluster).
step_merge() {
  kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: e3-merge
  namespace: ${NS}
  labels: { app: greenhouse-e3, experiment: merge }
spec:
  backoffLimit: 2
  ttlSecondsAfterFinished: 86400
  template:
    metadata:
      labels: { app: greenhouse-e3, experiment: merge }
    spec:
      restartPolicy: Never
      containers:
        - name: merge
          image: ${IMAGE_REF}
          imagePullPolicy: IfNotPresent
          workingDir: /app/own-article
          command: ["sh","-c"]
          args:
            - >
              python run_knockout_ablation.py --merge --out /results/knockout &&
              python run_multiseason.py       --merge --out /results/multiseason &&
              python run_oracle_parity.py     --merge --out /results/oracle_parity
          volumeMounts:
            - { name: results, mountPath: /results }
      volumes:
        - name: results
          persistentVolumeClaim: { claimName: e3-results }
EOF
  kubectl -n "$NS" wait --for=condition=complete --timeout=1800s job/e3-merge || true
  kubectl -n "$NS" logs -l experiment=merge --prefix --tail=-1
}

# Copy the merged CSVs off the PVC. A PVC needs a running pod to be cp'd from, so spin a
# tiny helper that just holds the volume mounted, then kubectl cp out of it.
step_pull() {
  kubectl -n "$NS" delete pod e3-puller --ignore-not-found
  kubectl -n "$NS" run e3-puller --image="$IMAGE_REF" --restart=Never \
    --overrides='{"spec":{"containers":[{"name":"c","image":"'"$IMAGE_REF"'","command":["sleep","3600"],"volumeMounts":[{"name":"r","mountPath":"/results"}]}],"volumes":[{"name":"r","persistentVolumeClaim":{"claimName":"e3-results"}}]}}'
  kubectl -n "$NS" wait --for=condition=Ready pod/e3-puller --timeout=300s
  mkdir -p "$REPO_ROOT/own-article/cluster/results_pull"
  kubectl -n "$NS" cp e3-puller:/results "$REPO_ROOT/own-article/cluster/results_pull"
  kubectl -n "$NS" delete pod e3-puller --ignore-not-found
  echo "pulled -> $REPO_ROOT/own-article/cluster/results_pull"
}

case "${1:-}" in
  kubeconfig)   step_kubeconfig ;;
  image)        step_image ;;
  pvc)          step_pvc ;;
  knockout)     step_knockout ;;
  multiseason)  step_multiseason ;;
  oracle)       step_oracle ;;
  watch)        step_watch ;;
  merge)        step_merge ;;
  pull)         step_pull ;;
  all)          step_pvc; step_knockout; step_multiseason; step_oracle; step_watch ;;
  *) echo "usage: bash submit.sh {kubeconfig|image|pvc|knockout|multiseason|oracle|watch|merge|pull|all}"; exit 1 ;;
esac
