#!/usr/bin/env python3
"""
Create database indexes for fast voter search.
Run this after importing voter data.
"""

import sys
sys.path.insert(0, ".")

from app import create_app, db


def create_indexes():
    app = create_app()

    with app.app_context():
        print("Creating search indexes...")

        try:
            # Enable pg_trgm extension
            db.session.execute(db.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            print("  pg_trgm extension enabled")

            # Set a lower similarity threshold for faster matching
            db.session.execute(db.text("SET pg_trgm.similarity_threshold = 0.1"))

            # B-tree index for prefix search (ILIKE 'xxx%')
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_voters_address_btree
                ON voters (residential_address1)
            """))
            print("  Created btree index on residential_address1")

            # GIN trigram index for fuzzy search
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_voters_address_trgm
                ON voters USING GIN (residential_address1 gin_trgm_ops)
            """))
            print("  Created trigram index on residential_address1")

            # GIN trigram index for name search
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_voters_name_trgm
                ON voters USING GIN (last_name gin_trgm_ops)
            """))
            print("  Created trigram index on last_name")

            # Analyze the table for query planner
            db.session.execute(db.text("ANALYZE voters"))
            print("  Analyzed voters table")

            db.session.commit()
            print("Done! Indexes created successfully.")

        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(create_indexes())
