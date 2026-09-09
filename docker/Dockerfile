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

ENV PATH="/orchardvision/.venv/bin:$PATH" \
    DATABASE_URL="sqlite:////data/orchardvision.db" \
    UPLOAD_DIR="/data/uploads" \
    PROCESSED_DIR="/data/processed" \
    ENVIRONMENT="production" \
    AUTO_CREATE_TABLES="true"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/api"]