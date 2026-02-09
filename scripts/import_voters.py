#!/usr/bin/env python3
"""
Import voter file data into the database.

Usage:
    python scripts/import_voters.py path/to/voter_file.csv

Expected CSV columns (Franklin County format):
    SOS_VOTERID, COUNTY_ID, FIRST_NAME, MIDDLE_NAME, LAST_NAME,
    RESIDENTIAL_ADDRESS1, RESIDENTIAL_ADDRESS2, RESIDENTIAL_CITY,
    RESIDENTIAL_STATE, RESIDENTIAL_ZIP, CITY, DATE_OF_BIRTH,
    REGISTRATION_DATE, PRECINCT_CODE, PRECINCT_NAME, WARD
"""

import csv
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, ".")

from app import create_app, db
from app.models import Voter


def parse_date(date_str: str):
    """Parse date string in various formats."""
    if not date_str:
        return None

    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def import_voters(csv_path: str, batch_size: int = 1000):
    """Import voters from CSV file."""
    app = create_app()

    with app.app_context():
        print(f"Importing voters from {csv_path}...")

        with open(csv_path, "r", encoding="cp1252") as f:
            reader = csv.DictReader(f)

            count = 0
            batch = []

            for row in reader:
                voter = Voter(
                    sos_voterid=row.get("SOS_VOTERID", "").strip(),
                    county_id=row.get("COUNTY_ID", "").strip(),
                    first_name=row.get("FIRST_NAME", "").strip(),
                    middle_name=row.get("MIDDLE_NAME", "").strip(),
                    last_name=row.get("LAST_NAME", "").strip(),
                    residential_address1=row.get("RESIDENTIAL_ADDRESS1", "").strip(),
                    residential_address2=row.get("RESIDENTIAL_ADDRESS2", "").strip(),
                    residential_city=row.get("RESIDENTIAL_CITY", "").strip(),
                    residential_state=row.get("RESIDENTIAL_STATE", "OH").strip() or "OH",
                    residential_zip=row.get("RESIDENTIAL_ZIP", "").strip(),
                    city=row.get("CITY", "").strip(),
                    date_of_birth=parse_date(row.get("DATE_OF_BIRTH", "")),
                    registration_date=parse_date(row.get("REGISTRATION_DATE", "")),
                    precinct_code=row.get("PRECINCT_CODE", "").strip(),
                    precinct_name=row.get("PRECINCT_NAME", "").strip(),
                    ward=row.get("WARD", "").strip(),
                )
                batch.append(voter)
                count += 1

                if len(batch) >= batch_size:
                    db.session.bulk_save_objects(batch)
                    db.session.commit()
                    print(f"  Imported {count} voters...")
                    batch = []

            # Save remaining
            if batch:
                db.session.bulk_save_objects(batch)
                db.session.commit()

        print(f"Done! Imported {count} voters total.")

        # Create indexes if they don't exist
        print("Ensuring trigram indexes exist...")
        try:
            db.session.execute(db.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_voters_address_trgm
                ON voters USING GIN (residential_address1 gin_trgm_ops)
            """))
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_voters_name_trgm
                ON voters USING GIN (last_name gin_trgm_ops)
            """))
            db.session.commit()
            print("Indexes created/verified.")
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")
            db.session.rollback()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_voters.py path/to/voter_file.csv")
        sys.exit(1)

    import_voters(sys.argv[1])
