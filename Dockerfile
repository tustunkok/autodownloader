# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Install ffmpeg and clean up apt cache in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install latest uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency manifests first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY src/ ./src/

# Ensure runtime directories exist
RUN mkdir -p data downloads logs

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "autodownloader.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
