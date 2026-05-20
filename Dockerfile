FROM python:3.11-slim

WORKDIR /app

# install pip dependencies (psycopg2-binary = no gcc needed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY . .

# create non-root user for security
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# expose Flask port
EXPOSE 5000

# health check (uses python instead of curl to avoid extra apt packages)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]

# run with gunicorn in production
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 3 --timeout 120 app:app
