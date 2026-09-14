#!/usr/bin/env bash
# Deploy OrchardVision to an Oracle Cloud "Always Free" VM (or any Ubuntu box).
#
# Run this script ON the server, from a clone of the repo:
#   git clone https://github.com/DerrickUnleashed/Mango.git && cd Mango
#   bash scripts/deploy-oracle.sh
#
# Steps: install Docker (Ubuntu only), write docker/.env, build & start the stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IS_UBUNTU=false
if [ -f /etc/os-release ]; then
  . /etc/os-release
  [ "${ID:-}" = "ubuntu" ] && IS_UBUNTU=true
fi

# --- 1. Ensure Docker + compose plugin -------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  if [ "$IS_UBUNTU" = true ]; then
    echo "Installing Docker CE..."
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker "$USER"
    echo "Docker installed. Log out / back in to use docker without sudo."
  else
    echo "ERROR: Docker not found. Install Docker first and re-run." >&2
    exit 1
  fi
fi
docker compose version

# --- 2. Environment --------------------------------------------------------
mkdir -p docker
ENV_FILE="docker/.env"
touch "$ENV_FILE"

if ! grep -q '^SECRET_KEY=' "$ENV_FILE" || [ "$(grep '^SECRET_KEY=' "$ENV_FILE" | cut -d= -f2)" = "change-me-in-production" ]; then
  SECRET="$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32)"
  if grep -q '^SECRET_KEY=' "$ENV_FILE"; then
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET/" "$ENV_FILE"
  else
    echo "SECRET_KEY=$SECRET" >> "$ENV_FILE"
  fi
  echo "Generated a random SECRET_KEY."
fi

if ! grep -q '^ALLOWED_ORIGINS=' "$ENV_FILE"; then
  PUBLIC_URL="${PUBLIC_URL:-}"
  if [ -z "$PUBLIC_URL" ]; then
    read -rp "Public URL (e.g. http://203.0.113.10:8080 or https://vision.example.com) []: " PUBLIC_URL
  fi
  if [ -n "$PUBLIC_URL" ]; then
    echo "ALLOWED_ORIGINS=[\"$PUBLIC_URL\"]" >> "$ENV_FILE"
    echo "CORS allowed for: $PUBLIC_URL"
  else
    echo "ALLOWED_ORIGINS=[\"http://localhost:8080\"]" >> "$ENV_FILE"
  fi
fi

echo "docker/.env contents:"
cat "$ENV_FILE"

# --- 3. Model weights (optional) -------------------------------------------
# The repo mounts ./models read-only. A fresh clone has no *.pt weights, which
# is fine (mock inference mode is the default). To enable real models, scp your
# weights to this machine:
#   scp -r models ubuntu@<server>:/path/to/Mango/
mkdir -p models

# --- 4. Build & start ------------------------------------------------------
echo "Building images (this takes a few minutes on first run)..."
docker compose -f docker/docker-compose.yml build

echo "Starting stack..."
docker compose -f docker/docker-compose.yml up -d

echo
echo "Deployed. The app should be reachable shortly at:"
echo "  http://<this-server>:${WEB_PORT:-8080}"
echo
echo "Check status with:"
echo "  docker compose -f docker/docker-compose.yml ps"
echo "  docker compose -f docker/docker-compose.yml logs -f api"