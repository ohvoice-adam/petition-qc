#!/bin/sh
set -e

echo "Enabling pg_trgm extension..."
python - <<'EOF'
import os
import psycopg2
url = os.environ["DATABASE_URL"]
conn = psycopg2.connect(url)
conn.autocommit = True
conn.cursor().execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
conn.close()
EOF

echo "Running database migrations..."
flask db upgrade

echo "Starting Gunicorn..."
exec gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 3600 \
    --worker-class sync \
    "app:create_app()"
