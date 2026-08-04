# E3 cluster-compute image (CPU) for the greenhouse-control own-article benchmark.
#
# Build CONTEXT is the repo root (greenhouse-control/), not this directory, so the COPY
# below can reach own-article/. submit.sh builds it as:
#     docker build -f own-article/cluster/Dockerfile -t greenhouse-e3:<tag> .
#
# Embarrassingly-parallel CPU workload -> a plain CPU image. The one image also serves the
# OPTIONAL nvidia.com/gpu PPO/SAC pods because the PyPI torch wheel is CUDA-capable
# (see requirements-cluster.txt).
FROM python:3.11-slim

# System libs needed by casadi / do_mpc (Fortran runtime for the bundled IPOPT) and by
# torch/numpy (OpenMP). casadi ships IPOPT in its wheel, so no system IPOPT is required.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc libgfortran5 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# pip goes through the cluster's local devpi PyPI mirror AUTOMATICALLY when these build
# args are supplied (cluster-runbook.md §18: local-first, fetch-through to pypi.org).
# submit.sh passes them; a plain `docker build` with no args falls back to public PyPI.
#   --build-arg PIP_INDEX_URL=http://devpi.jupyterhub.svc.cluster.local:3141/root/pypi/+simple/
#   --build-arg PIP_TRUSTED_HOST=devpi.jupyterhub.svc.cluster.local
ARG PIP_INDEX_URL=""
ARG PIP_TRUSTED_HOST=""
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (Docker layer cache): only re-installs when the pin file changes.
COPY own-article/cluster/requirements-cluster.txt /app/requirements-cluster.txt
# gl_gym pins numpy<2.0, but the pysindy 2.1.0 wheel declares numpy>=2.0 in its metadata
# (it runs correctly on numpy 1.26.4 regardless). A single `pip install -r` therefore
# fails with a resolver conflict, so install everything else first (numpy<2.0 wins), then
# add pysindy WITHOUT its declared deps — exactly how the reference venv was assembled.
RUN grep -v '^pysindy' /app/requirements-cluster.txt > /app/req-core.txt \
    && python -m pip install --no-cache-dir -r /app/req-core.txt \
    && python -m pip install --no-cache-dir --no-deps pysindy==2.1.0

# pysindy was installed --no-deps (to hold numpy<2.0, since its wheel declares numpy>=2.0);
# that ALSO skipped its other required deps. Reinstate them in a SEPARATE layer so the big
# CUDA-torch layer above stays cached. `derivative` needs only numpy>=1.18.3, so numpy 1.26.4
# is left untouched (the whole reason for --no-deps).
RUN python -m pip install --no-cache-dir "derivative>=0.6.2" typing_extensions

# gl_gym's PyPI wheel does NOT ship the Rostov-on-Don ERA5 weather CSVs (2018-2023); they
# live in the GreenLight-Gym2 source (greenlight/GreenLight-Gym2/gl_gym/data/weather/) and
# were injected into the reference venv by hand. Bake them into the installed package so
# env.reset() finds them. Stage them into the build context first:
#   mkdir -p own-article/cluster/weather && cp -r <GreenLight-Gym2>/gl_gym/data/weather/Rostov-on-Don own-article/cluster/weather/
COPY own-article/cluster/weather/Rostov-on-Don/ /usr/local/lib/python3.11/site-packages/gl_gym/data/weather/Rostov-on-Don/

# The article compute code is a set of loose scripts (article_experiment_utils.py,
# protocol_config.py, rostov_soil.py, run_*.py, merge_*.py) that add their own dir to
# sys.path; no `pip install` of the project is needed. gl_gym ships the Rostov weather
# data inside the wheel, so no dataset volume is required for the input side.
COPY own-article/ /app/own-article/

WORKDIR /app/own-article

# Torch oversubscribes cores when many seed-pods share a node; the runners also call
# torch.set_num_threads(1), this is a belt-and-braces default for BLAS/OpenMP too.
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

# No default CMD: each Job/pod supplies its own `command:` (the run_*.py shard invocation).
# Sanity smoke (build-time, optional): python run_knockout_ablation.py --seeds 0 --fast 1 --tag build
