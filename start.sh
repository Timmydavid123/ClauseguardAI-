#!/bin/bash

# start.sh - Entrypoint script for ClauseGuard Docker container

set -e  # Exit immediately if a command exits with a non-zero status

echo "🚀 Starting ClauseGuard..."

# Print environment info
echo "Python version: $(python --version)"
echo "Django version: $(python -m django --version)"
echo "Working directory: $(pwd)"

# Run database migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Check if migrations were successful
if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed"
    exit 1
fi

# Collect static files (if needed)
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Create cache table (if using database cache)
echo "📦 Creating cache table..."
python manage.py createcachetable --database default || true

# Start Celery worker in background
echo "🔄 Starting Celery worker..."
celery -A clauseguard worker \
    --loglevel=info \
    --concurrency=1 \
    --max-tasks-per-child=10 \
    --max-memory-per-child=150000 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --pidfile=/tmp/celery.pid &
CELERY_PID=$!
echo "✅ Celery worker started with PID: $CELERY_PID"

# Optional: Start Celery beat (if you have scheduled tasks)
# echo "🔄 Starting Celery beat..."
# celery -A clauseguard beat --loglevel=info --pidfile=/tmp/celery-beat.pid &
# CELERY_BEAT_PID=$!
# echo "✅ Celery beat started with PID: $CELERY_BEAT_PID"

# Start Gunicorn with proper settings
echo "🌐 Starting Gunicorn server..."
exec gunicorn clauseguard.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance

# Note: The exec above replaces the shell process with Gunicorn
# If Gunicorn exits, the container will stop

# Cleanup function (won't be called due to exec, but kept for completeness)
cleanup() {
    echo "🛑 Shutting down..."
    
    # Stop Celery worker
    if [ -n "$CELERY_PID" ] && kill -0 $CELERY_PID 2>/dev/null; then
        echo "Stopping Celery worker (PID: $CELERY_PID)..."
        kill -TERM $CELERY_PID
        wait $CELERY_PID 2>/dev/null
    fi
    
    # Stop Celery beat if running
    if [ -n "$CELERY_BEAT_PID" ] && kill -0 $CELERY_BEAT_PID 2>/dev/null; then
        echo "Stopping Celery beat (PID: $CELERY_BEAT_PID)..."
        kill -TERM $CELERY_BEAT_PID
        wait $CELERY_BEAT_PID 2>/dev/null
    fi
    
    echo "👋 Goodbye!"
    exit 0
}

# Set up trap for graceful shutdown (won't be called due to exec)
trap cleanup SIGTERM SIGINT