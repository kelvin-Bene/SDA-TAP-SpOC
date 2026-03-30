# Demo Backend Dockerfile: Python 3.12 only (no Java/Orekit)
# Uses DuckDB for database, no Supabase connection needed

FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency spec and install
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir "."

# Copy application code
COPY uct_benchmark/ ./uct_benchmark/
COPY backend_api/ ./backend_api/
COPY start.py ./

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DEMO_MODE=true \
    DATABASE_BACKEND=duckdb

RUN mkdir -p /app/data/uploads /app/data/database

# Non-root user
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 --ingroup appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "start.py"]
