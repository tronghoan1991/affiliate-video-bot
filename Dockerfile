FROM python:3.11-slim

# Cài ffmpeg (bắt buộc cho video processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Tạo thư mục outputs tạm
RUN mkdir -p /tmp/affiliatebot_outputs

EXPOSE 5000

# Dùng gunicorn cho production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "app:flask_app"]
