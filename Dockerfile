# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Starting ClauseGuard on Render..."\n\
\n\
# Run migrations\n\
python manage.py migrate --noinput\n\
\n\
# Collect static files\n\
python manage.py collectstatic --noinput\n\
\n\
# Check if this is the worker service\n\
if [ "$RENDER_WORKER" = "true" ] || [[ "$@" == *"celery"* ]]; then\n\
    echo "🔄 Starting Celery worker..."\n\
    \n\
    # Wait a bit for Redis to be ready (Render handles this, but just in case)\n\
    sleep 5\n\
    \n\
    # Start Celery worker\n\
    exec celery -A clauseguard worker \\\n\
        --loglevel=info \\\n\
        --concurrency=1\n\
else\n\
    echo "🌐 Starting Gunicorn server..."\n\
    # Start Gunicorn\n\
    exec gunicorn clauseguard.wsgi:application \\\n\
        --bind 0.0.0.0:$PORT \\\n\
        --workers 2 \\\n\
        --timeout 120 \\\n\
        --access-logfile - \\\n\
        --error-logfile -\n\
fi\n\
' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]