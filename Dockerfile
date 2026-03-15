FROM python:3.14-slim

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

# For testing purposes, uncomment the following lines to set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO


CMD ["uv", "run", "GreeMQTT"]