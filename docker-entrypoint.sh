#!/bin/sh
set -e

echo "Enabling pg_trgm extension..."
python - <<'PYEOF'
import os, psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
conn.cursor().execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
conn.close()
PYEOF

# Detect whether this is a brand-new database (no alembic_version table yet).
# Fresh installs use db.create_all() + stamp; existing installs use migrate.
FRESH_DB=$(python - <<'PYEOF'
import os, psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("""
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'alembic_version'
    )
""")
print("0" if cur.fetchone()[0] else "1")
conn.close()
PYEOF
)

if [ "$FRESH_DB" = "1" ]; then
    echo "Fresh database detected — creating tables with db.create_all()..."
    python - <<'PYEOF'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
PYEOF
    echo "Stamping migrations as current..."
    flask db stamp head
else
    echo "Existing database — running migrations..."
    flask db upgrade
fi

echo "Starting Gunicorn..."
exec gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 3600 \
    --worker-class sync \
    "app:create_app()"
