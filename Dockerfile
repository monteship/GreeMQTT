# Stage 1: Build
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies into /install
RUN pip install --no-cache-dir --disable-pip-version-check --prefix=/install .

# Stage 2: Final Image
FROM python:3.13-slim
LABEL authors="monteship"
LABEL description="MQTT client for monitoring and controlling devices"

RUN mkdir -p /app && chmod 777 /app

# Create a non-root user and group
RUN useradd --create-home appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy only necessary project files
COPY GreeMQTT /app/GreeMQTT
COPY healthcheck.py /app/healthcheck.py

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

# For testing purposes, uncomment the following lines to set environment variables
#ENV PYTHONUNBUFFERED=1 \
#    PYTHONDONTWRITEBYTECODE=1 \
#    LOG_LEVEL=INFO \
#    NETWORK="192.168.1.40,192.168.1.41" \
#    MQTT_BROKER="192.168.1.10"

# Use non-root user
USER appuser

EXPOSE 1883

# Health check to monitor container health
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

CMD ["python", "-m", "GreeMQTT"]
