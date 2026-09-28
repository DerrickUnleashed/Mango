#!/bin/sh
set -e

# Fix ownership of data directories (volume may have been created by root)
chown -R orchard:orchard /data

# Apply database migrations before starting the application.
#
# This runs only for the API service (RUN_MIGRATIONS=true in
# docker-compose.yml). The worker deliberately does not set it: both share
# the same SQLite file, and two processes racing on the same migration is a
# worse failure than one skipping it. The API must be up before work is
# queued, so gating on it is sufficient.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "entrypoint: applying database migrations"
    runuser -u orchard -- python /orchardvision/apps/api/migrate.py
    echo "entrypoint: migrations applied"
fi

# Drop to orchard user and exec the actual command
exec runuser -u orchard -- "$@"
