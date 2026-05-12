# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# runtime dependencies only 
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# copy installed Python packages from builder
COPY --from=builder /install /usr/local

# copy application code
COPY . .

# create non-root user for security
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# expose Flask port
EXPOSE 5000

# health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# run with gunicorn in production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "app:app"]
