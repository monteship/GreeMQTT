FROM python:3.13-slim
LABEL authors="monteship"

# Stage 1: Build
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final Image
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 1883
CMD ["python", "main.py"]

