# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies for scientific Python packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition first to maximize layer caching.
COPY pyproject.toml ./
COPY src/mt_oil/__init__.py ./src/mt_oil/__init__.py

# Install the package and its dependencies. Wheels are cached in pip.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e "."

# --- Runtime image ---
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Create a non-root user for security.
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed Python packages from builder.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src ./src

# Copy application source.
COPY src ./src

# Install any system runtime deps (none needed for slim python + numpy wheels).
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "mt_oil.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
