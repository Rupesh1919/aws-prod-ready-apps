# Multi-stage build for Claims API
# Uses Python 3.11 on Debian Bookworm (current stable)

# Build stage
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim-bookworm

# Create non-root user
RUN groupadd -r claims && useradd -r -g claims -u 1000 claims

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/claims/.local

# Set Python path for user-installed packages
ENV PATH=/home/claims/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY --chown=claims:claims claims_api /app/claims_api
COPY --chown=claims:claims alembic /app/alembic
COPY --chown=claims:claims alembic.ini /app/

# Create writable directory for Alembic (if needed)
RUN mkdir -p /app/tmp && chown claims:claims /app/tmp

# Switch to non-root user
USER claims

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

# Expose application port (unprivileged)
EXPOSE 8000

# Default command - runs Uvicorn without reload
CMD ["python", "-m", "uvicorn", "claims_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
