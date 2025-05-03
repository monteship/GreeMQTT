# Stage 1: Build
FROM python:3.13-slim AS builder
LABEL authors="monteship"

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
COPY config.py device.py device_db.py encryptor.py main.py managers.py mqtt_handler.py utils.py README.md /app/


# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOGURU_LEVEL=INFO

# Use non-root user
USER appuser

EXPOSE 1883

CMD ["python", "main.py"]

