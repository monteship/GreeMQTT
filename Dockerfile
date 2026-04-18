# --- Stage 1: Build dependencies ---
FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential libffi-dev && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

ENV UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY GreeMQTT /app/GreeMQTT/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Stage 2: Final runtime image ---
FROM python:3.14-slim
WORKDIR /app

COPY --from=builder /app /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

CMD ["/app/.venv/bin/python", "-m", "GreeMQTT"]
