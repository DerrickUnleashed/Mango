#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🚀 Starting a clean Docker Compose rebuild..."

# Force a clean rebuild of the images ignoring the cache
docker compose -f docker/docker-compose.yml build --no-cache

# Recreate and start the containers
docker compose -f docker/docker-compose.yml up --force-recreate

echo "✅ Containers are up and running!"