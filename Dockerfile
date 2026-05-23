# ══════════════════════════════════════════════════════════════════════════════
# Dockerfile — Affiliate Video Bot v5
# Deploy lên Render Web Services
# ══════════════════════════════════════════════════════════════════════════════

FROM python:3.10-slim

# Cài ffmpeg (cần cho video processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements trước để cache layer
COPY requirements.txt .

# Cài Python packages (bỏ torch nặng — Render chỉ chạy web server + bot)
RUN pip install --no-cache-dir \
    python-telegram-bot==21.6 \
    flask \
    requests \
    aiohttp \
    python-dotenv \
    Pillow \
    numpy \
    tqdm

# Copy toàn bộ source
COPY . .

# Render inject PORT tự động qua env var
ENV PORT=8080

# Chạy app (Flask + Telegram bot chạy song song)
CMD ["python", "app.py"]
