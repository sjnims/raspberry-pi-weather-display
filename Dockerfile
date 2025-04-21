# syntax=docker/dockerfile:1.7

# ───────────── base layer ─────────────
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/opt/poetry/bin:$PATH"

RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

# ───────────── deps layer (cache‑able) ─────────────
COPY pyproject.toml poetry.lock* ./
RUN poetry install --with dev --no-root

# ───────────── source layer ─────────────
COPY README.md ./
COPY src ./src
COPY templates ./templates
COPY static ./static
COPY tests ./tests
COPY deploy ./deploy

# Install the project itself (editable) to generate scripts
RUN . .venv/bin/activate && pip install -e .

# ───────────── dev image ─────────────
FROM base AS dev
ENV PYTHONPATH="/app/src:$PYTHONPATH" \
    PATH="/app/.venv/bin:$PATH"

# auto‑activate venv
CMD ["/bin/bash", "-c", "source /app/.venv/bin/activate && exec bash"]