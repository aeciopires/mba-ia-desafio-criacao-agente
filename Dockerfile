# syntax=docker/dockerfile:1
# Multi-architecture image (linux/amd64, linux/arm64) for the Residencial Aurora API.

FROM ghcr.io/astral-sh/uv:0.12.24 AS uv

FROM python:3.12.15-slim-trixie AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Dependencies first, for layer caching.
COPY pyproject.toml uv.lock VERSION README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12.15-slim-trixie AS runtime
ARG AURORA_VERSION=0.0.0
ARG UID=1000
ARG GID=1000
LABEL org.opencontainers.image.title="aurora-api" \
      org.opencontainers.image.description="Residencial Aurora virtual assistant (Google ADK + FastAPI)" \
      org.opencontainers.image.version="${AURORA_VERSION}" \
      org.opencontainers.image.licenses="MIT"
RUN groupadd --gid "${GID}" aurora 2>/dev/null || true \
    && useradd --uid "${UID}" --gid "${GID}" --no-create-home --shell /usr/sbin/nologin aurora 2>/dev/null || true
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY VERSION ./VERSION
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    AURORA_DADOS_DIR=/app/dados \
    AURORA_DB_PATH=/app/var/aurora.db \
    API_HOST=0.0.0.0 \
    API_PORT=8000
RUN mkdir -p /app/var && chown "${UID}:${GID}" /app/var
USER ${UID}:${GID}
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=12 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["python", "-m", "aurora"]
