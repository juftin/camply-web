#!/usr/bin/env bash

set -e

# Ensure cache directory is writable; fall back to /tmp on Linux where
# Docker may create bind mount directories as root
CACHE_DIR="${HOME}/.local/share/camply"
if [ ! -d "${CACHE_DIR}" ] || [ ! -w "${CACHE_DIR}" ]; then
    FALLBACK_CACHE="/tmp/camply-cache"
    mkdir -p "${FALLBACK_CACHE}"
    echo "Warning: ${CACHE_DIR} not writable, using ${FALLBACK_CACHE}" >&2
    export CAMPLY_CACHE_DIR="${FALLBACK_CACHE}"
fi

# Create Prometheus multiprocess directory if configured
if [ -n "${PROMETHEUS_MULTIPROC_DIR}" ]; then
    mkdir -p "${PROMETHEUS_MULTIPROC_DIR}"
fi

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
    cd /app/packages/db
    alembic upgrade head
fi

exec "${@}"
