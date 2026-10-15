# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

WORKDIR /orchardvision

# Copy workspace manifests for dependency installation
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY ml/pyproject.toml ml/pyproject.toml

# Stage the source for the API and ML packages
COPY apps/api apps/api
COPY ml ml

# The fine-tuned detector, the only weight needed for a working boot. Placed at
# the exact path settings.yolo_weights_path defaults to
# (ROOT_DIR/models/mango_yolov8n-4/weights/best.pt) so no env var is needed to
# point the app at it. Everything else stays out: docker/bootstrap_weights.py
# fetches TAPNext++ (2.4G) on boot instead.
COPY models/mango_yolov8n-4/weights/best.pt models/mango_yolov8n-4/weights/best.pt

# Image size matters here: the API runs on CPU (and on Apple MPS locally), but
# uv.lock pins the CUDA build of torch, which drags in ~5G of packages that do
# nothing on a CPU-only host (nvidia/* 3.3G, triton 815M, cuda/*). uv also
# leaves its ~5.7G download cache in /root. Between them that took the image to
# 19.3G, which no managed host accepts.
#
# UV_TORCH_BACKEND alone cannot fix this: the lockfile wins over the index
# hint. So swap torch for its CPU build explicitly, then drop the now-orphaned
# CUDA packages and the cache.
ENV UV_TORCH_BACKEND=cpu

RUN uv sync --project apps/api --no-dev --no-cache \
    && uv pip install --python /orchardvision/.venv/bin/python \
        --index-url https://download.pytorch.org/whl/cpu --reinstall torch \
    && find /orchardvision/.venv -maxdepth 4 -type d \
        \( -name nvidia -o -name triton -o -name 'cuda' -o -name 'cuda_*' \) \
        -exec rm -rf {} + \
    && uv cache clean --force || true

# `ultralytics` (pulled in by the `ml` package) depends on the GUI build of
# opencv, which links against X11 (libxcb.so.1 and friends) that a server image
# has no use for. Both packages ship the same `cv2` module, so whichever wins
# the import race decides whether the API boots at all. Drop the GUI build and
# restore headless so the outcome stops depending on install order.
RUN uv pip uninstall --python /orchardvision/.venv/bin/python opencv-python \
    && uv pip install --python /orchardvision/.venv/bin/python \
        --reinstall --no-deps opencv-python-headless

RUN groupadd -r orchard && useradd -r -g orchard -d /orchardvision -s /sbin/nologin orchard \
    && mkdir -p /data/uploads /data/processed \
    && chown -R orchard:orchard /orchardvision /data

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/bootstrap_weights.py /bootstrap_weights.py
RUN chmod +x /entrypoint.sh /bootstrap_weights.py

ENV PATH="/orchardvision/.venv/bin:$PATH" \
    DATABASE_URL="sqlite:////data/orchardvision.db" \
    UPLOAD_DIR="/data/uploads" \
    PROCESSED_DIR="/data/processed" \
    ENVIRONMENT="production" \
    AUTO_CREATE_TABLES="true"

# Model weights are NOT all baked into the image. TAPNext++ alone is 2.4G, which
# would dominate the build context and blow past most hosts' image limits; the
# rest is fetched on first boot by docker/bootstrap_weights.py.
#
# This deliberately defaults to the same tree settings.yolo_weights_path and
# settings.tapnext_checkpoint_path already resolve against (ROOT_DIR/models/),
# so a weight fetched at boot lands exactly where the app looks for it. Pointing
# these at different roots is how a deploy ends up downloading 2.4G that nothing
# ever reads.
ENV WEIGHTS_DIR="/orchardvision/models"

EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]
# PORT is injected by managed hosts (Railway, Render, Fly). Defaulting to 8001
# keeps docker-compose working unchanged, where the port is passed explicitly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001} --app-dir apps/api"]