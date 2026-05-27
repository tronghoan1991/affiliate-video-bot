FROM python:3.11-slim

WORKDIR /app

# System deps (minimal for free plan)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

EXPOSE 5000

# Gunicorn: 1 worker để tránh OOM trên free plan 512MB
CMD gunicorn app:flask_app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 500 \
    --max-requests-jitter 50 \
