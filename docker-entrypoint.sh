#!/bin/sh
set -e

echo "Running database migrations..."
flask db upgrade

echo "Starting Gunicorn..."
exec gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 3600 \
    --worker-class sync \
    "app:create_app()"
