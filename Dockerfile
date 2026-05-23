FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cấu hình apt retry trước khi update
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
 && echo 'Acquire::http::Timeout "60";' >> /etc/apt/apt.conf.d/80-retries \
 && echo 'Acquire::https::Timeout "60";' >> /etc/apt/apt.conf.d/80-retries

# Chỉ cài những gì thực sự cần (Render chỉ chạy Flask + Telegram bot)
# ffmpeg / libsm6 / opencv KHÔNG cần ở Render — AI processing ở Colab
RUN apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get update -o Acquire::ForceIPv4=true \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "app:flask_app"]
