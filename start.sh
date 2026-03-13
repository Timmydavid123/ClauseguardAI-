#!/bin/bash

# start.sh - Entrypoint script for ClauseGuard

set -e

echo "🚀 Starting ClauseGuard..."

echo "Python version: $(python --version)"
echo "Django version: $(python -m django --version)"
echo "Working directory: $(pwd)"

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Create cache table if using DB cache
python manage.py createcachetable --database default || true

# Start Gunicorn
echo "🌐 Starting Gunicorn server..."
exec gunicorn clauseguard.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -