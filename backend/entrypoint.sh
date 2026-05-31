#!/usr/bin/env bash

set -e

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
    cd /app/packages/db
    alembic upgrade head

    if [ "${SKIP_POPULATE:-0}" != "1" ]; then
        populate-database
    fi
fi

exec "${@}"
