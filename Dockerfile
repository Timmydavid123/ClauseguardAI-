# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including redis-tools for health checks
RUN apt-get update && apt-get install -y \
    redis-tools \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create startup scripts
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Starting ClauseGuard..."\n\
\n\
# Run migrations (only in web service, but safe to run everywhere)\n\
python manage.py migrate --noinput\n\
\n\
# Collect static files\n\
python manage.py collectstatic --noinput\n\
\n\
# Check what service we are running as\n\
if [ "$SERVICE_TYPE" = "worker" ] || [[ "$@" == *"celery"* ]]; then\n\
    echo "🔄 Starting Celery worker..."\n\
    \n\
    # Wait for Redis\n\
    echo "Waiting for Redis at $REDIS_URL..."\n\
    max_retries=30\n\
    counter=0\n\
    until redis-cli -u "$REDIS_URL" ping 2>/dev/null || [ $counter -eq $max_retries ]; do\n\
        echo "Redis not ready yet... ($counter/$max_retries)"\n\
        sleep 2\n\
        counter=$((counter+1))\n\
    done\n\
    \n\
    if [ $counter -eq $max_retries ]; then\n\
        echo "Failed to connect to Redis"\n\
        exit 1\n\
    fi\n\
    \n\
    echo "Redis is ready!"\n\
    \n\
    # Start Celery worker\n\
    exec celery -A clauseguard worker --loglevel=info\n\
else\n\
    echo "🌐 Starting Gunicorn server..."\n\
    # Start Gunicorn\n\
    exec gunicorn clauseguard.wsgi:application \\\n\
        --bind 0.0.0.0:8000 \\\n\
        --workers 2 \\\n\
        --timeout 120 \\\n\
        --access-logfile - \\\n\
        --error-logfile -\n\
fi\n\
' > /start.sh && chmod +x /start.sh

# Default command
CMD ["/start.sh"]