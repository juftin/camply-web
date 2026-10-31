ARG PYTHON_VERSION=3.14
FROM node:24-bookworm-slim AS node
FROM ghcr.io/astral-sh/uv:latest AS uv

FROM python:${PYTHON_VERSION}-slim-bookworm AS python-base
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_LOCKED=1 \
    VIRTUAL_ENV=/app/.venv

FROM python-base AS application-build
# Only this shared build stage needs JavaScript tooling.
COPY --from=node /usr/local/ /usr/local/
RUN corepack enable pnpm && corepack prepare pnpm@12.15.0 --activate
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .python-version ./
COPY src/ src/
ARG VITE_ENABLE_COMMUNITY_PAGES=false
ARG VITE_MAP_TILE_URL
ARG VITE_MAP_ATTRIBUTION_TEXT
ARG VITE_MAP_ATTRIBUTION_URL
ARG VITE_MAP_MAX_NATIVE_ZOOM=19
ENV VITE_ENABLE_COMMUNITY_PAGES=$VITE_ENABLE_COMMUNITY_PAGES \
    VITE_MAP_TILE_URL=$VITE_MAP_TILE_URL \
    VITE_MAP_ATTRIBUTION_TEXT=$VITE_MAP_ATTRIBUTION_TEXT \
    VITE_MAP_ATTRIBUTION_URL=$VITE_MAP_ATTRIBUTION_URL \
    VITE_MAP_MAX_NATIVE_ZOOM=$VITE_MAP_MAX_NATIVE_ZOOM
RUN uv build --out-dir dist

FROM python-base AS camply
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl nginx && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --system --gid 1000 camply && \
    adduser --system --uid 1000 --gid 1000 camply
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra server --extra distributed --extra postgres --extra sentry --no-install-project
COPY --from=application-build /app/dist/ /app/dist/
RUN uv pip install --no-deps /app/dist/*.whl && rm -rf /app/dist
COPY deploy/entrypoint.sh /app/entrypoint.sh
ENV PATH="/app/.venv/bin:${PATH}" \
    HOME=/home/camply
RUN mkdir -p ${HOME}/.local/share/camply && \
    chown camply:camply /app && \
    chown -R camply:camply ${HOME}
USER camply
EXPOSE 8000 8080
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["camply", "backend", "serve"]
