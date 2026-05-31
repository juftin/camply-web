#!/usr/bin/env bash

set -e

cd /app/packages/db
alembic upgrade head

if [ "${SKIP_POPULATE:-0}" != "1" ]; then
    populate-database
fi

exec "${@}"
