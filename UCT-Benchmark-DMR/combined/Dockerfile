# Backend Dockerfile: Java 17 (Orekit) + Python 3.12 (FastAPI)
# Orekit JVM uses ~500MB per worker, so limit uvicorn workers to 2.

FROM eclipse-temurin:17-jdk-jammy AS base

# Install Python 3.12 from deadsnakes PPA
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-venv \
        python3.12-dev && \
    rm -rf /var/lib/apt/lists/*

# Set python3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install pip
RUN python3.12 -m ensurepip --upgrade && \
    python3.12 -m pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Copy dependency spec first for layer caching
COPY pyproject.toml ./

# Install Python dependencies (with postgres extras for production)
RUN pip install --no-cache-dir ".[postgres]"

# Copy application code
COPY uct_benchmark/ ./uct_benchmark/
COPY backend_api/ ./backend_api/

# Set environment
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DATABASE_BACKEND=postgres

# Create uploads directory
RUN mkdir -p /app/data/uploads

EXPOSE 8000

# Health check using Python's urllib (no curl in base image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with 2 workers (Orekit JVM memory constraint)
CMD ["python3", "-m", "uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
