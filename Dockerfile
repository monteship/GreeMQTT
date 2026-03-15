FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

ENV UV_NO_DEV=1

ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    pkg-config \
    rustc \
    cargo && \
    rm -rf /var/lib/apt/lists/*


RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy project files
COPY pyproject.toml uv.lock /app/
RUN pip install uv
RUN uv sync --frozen --no-dev --no-install-project

COPY GreeMQTT /app/GreeMQTT/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:$PYTHONPATH" \
    LOG_LEVEL=INFO \
    MQTT_BROKER=192.168.1.100


CMD ["uv", "run", "GreeMQTT"]
