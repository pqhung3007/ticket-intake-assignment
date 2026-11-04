# syntax=docker/dockerfile:1
# Backend image for local development (docker compose). The production image is the
# repository-root Dockerfile, which also bundles the built frontend.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH
RUN pip install --no-cache-dir uv==0.11.32
WORKDIR /app

FROM base AS dev
# Dependencies first, in their own layer: code edits don't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]
