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

RUN uv sync --project apps/api --no-dev

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

# Model weights are NOT baked into the image. TAPNext++ alone is 2.4G, which
# would dominate the build context and blow past most hosts' image limits. They
# are fetched on first boot into WEIGHTS_DIR by docker/bootstrap_weights.py
# (see WEIGHTS_* env vars there), and cached on a mounted volume when one
# exists.
ENV WEIGHTS_DIR="/data/models"

EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]
# PORT is injected by managed hosts (Railway, Render, Fly). Defaulting to 8001
# keeps docker-compose working unchanged, where the port is passed explicitly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001} --app-dir apps/api"]