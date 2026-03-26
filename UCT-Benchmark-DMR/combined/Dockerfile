# Backend Dockerfile: Java 17 (Orekit) + Python 3.12 (FastAPI)
# Orekit data loaded from pip package (from_pip_library=True), no local copy needed.

FROM eclipse-temurin:17-jre-jammy AS base

# Install Python 3.12 + build deps for native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        gcc \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Set python3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install pip
RUN python3.12 -m ensurepip --upgrade && \
    python3.12 -m pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Copy dependency spec + README (required by hatchling metadata)
COPY pyproject.toml README.md ./

# Remove system cryptography to avoid conflicts with pip version
RUN apt-get update && apt-get remove -y python3-cryptography 2>/dev/null; rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "."

# Copy application code
COPY uct_benchmark/ ./uct_benchmark/
COPY backend_api/ ./backend_api/
COPY start.py ./

# Set environment — JVM memory limits for Orekit
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    JAVA_TOOL_OPTIONS="-Xmx256m -XX:+UseSerialGC -XX:MaxMetaspaceSize=128m"

# Create uploads directory
RUN mkdir -p /app/data/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "start.py"]
