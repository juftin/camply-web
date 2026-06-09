#!/usr/bin/env bash

set -e

# Ensure cache directory is writable. On Linux, Docker bind-mounts
# are created as root:root, so the camply user cannot write to them.
# Replace the unwritable directory with a symlink to /tmp.
CACHE_DIR="${HOME}/.local/share/camply"
if [ ! -d "${CACHE_DIR}" ] || [ ! -w "${CACHE_DIR}" ]; then
    FALLBACK_CACHE="/tmp/camply-cache"
    mkdir -p "${FALLBACK_CACHE}"
    # rmdir only succeeds on empty directories — safe against data loss.
    # Bind-mount directories are usually empty on first start.
    rmdir "${CACHE_DIR}" 2>/dev/null || true
    if [ ! -e "${CACHE_DIR}" ]; then
        mkdir -p "$(dirname "${CACHE_DIR}")"
        ln -sf "${FALLBACK_CACHE}" "${CACHE_DIR}"
        echo "Cache dir redirected to ${FALLBACK_CACHE}" >&2
    fi
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
