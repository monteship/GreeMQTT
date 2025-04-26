FROM python:3.13-slim
LABEL authors="monteship"

# Stage 1: Build
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final Image
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 1883
CMD ["python", "main.py"]

