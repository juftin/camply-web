#!/usr/bin/env bash

set -e

# Create Prometheus multiprocess directory if configured
if [ -n "${PROMETHEUS_MULTIPROC_DIR}" ]; then
    mkdir -p "${PROMETHEUS_MULTIPROC_DIR}"
fi

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
    cd /app/packages/db
    alembic upgrade head

    if [ "${SKIP_POPULATE:-0}" != "1" ]; then
        populate-database
    fi
fi

exec "${@}"
