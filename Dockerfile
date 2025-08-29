FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock /app/
RUN pip install uv
RUN uv sync --frozen --no-dev --no-install-project

COPY GreeMQTT /app/GreeMQTT/
COPY healthcheck.py /app/healthcheck.py

# For testing purposes, uncomment the following lines to set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO


# Health check to monitor container health
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

CMD ["uv", "run", "GreeMQTT"]
