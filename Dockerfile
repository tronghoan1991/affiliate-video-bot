FROM python:3.11-slim

WORKDIR /app

# Cài hệ thống deps tối thiểu
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước để tận dụng Docker layer cache
COPY requirements_dispatcher.txt .
RUN pip install --no-cache-dir -r requirements_dispatcher.txt

# Copy source code
COPY dispatcher.py .

# Render inject PORT tự động (mặc định 10000)
ENV PORT=10000

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["python", "-u", "dispatcher.py"]
