from sqlalchemy import text

from app import db
from app.models import Settings


class StatsService:
    """Service for calculating signature verification statistics."""

    @staticmethod
    def get_target_city_info() -> dict:
        """Get the target city configuration."""
        city = Settings.get_target_city()
        return {
            "city": city,
            "display": Settings.get_target_city_display(),
            "pattern": Settings.get_target_city_pattern(),
        }

    @staticmethod
    def get_progress_stats() -> dict:
        """
        Get overall signature verification progress statistics.

        Returns dict with:
            - entered: Total signatures entered
            - matched_target: Matched signatures from target city residents
            - matched_other: Matched signatures from non-target city residents
            - address_only_target: Address-only matches from target city
            - address_only_other: Address-only matches from non-target city
            - unmatched: Signatures with no voter match
            - percent_verified: Percentage of verified target city signatures
            - percent_target: Percentage of all signatures from target city addresses
            - target_city: The configured target city name
        """
        city_info = StatsService.get_target_city_info()
        city_pattern = city_info["pattern"]

        sql = text("""
            SELECT
                count(*) as entered,
                sum(
                    case when matched is true
                    and registered_city like :city_pattern then 1 else 0 end
                ) as matched_target,
                sum(
                    case when matched is true
                    and (
                        registered_city not like :city_pattern or registered_city is null
                    ) then 1 else 0 end
                ) as matched_other,
                sum(
                    case when matched is false
                    and registered_city like :city_pattern then 1 else 0 end
                ) as address_only_target,
                sum(
                    case when matched is false
                    and (
                        registered_city not like :city_pattern or registered_city is null
                    )
                    and residential_zip <> '' then 1 else 0 end
                ) as address_only_other,
                sum(
                    case when residential_zip is null
                    or residential_zip = '' then 1 else 0 end
                ) as unmatched,
                round(
                    (
                        sum(
                            case when matched is true
                            and registered_city like :city_pattern then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_verified,
                round(
                    (
                        sum(
                            case when registered_city like :city_pattern then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_target
            FROM (
                -- Keep all rows with NULL or empty sos_voterid
                SELECT * FROM signatures
                WHERE sos_voterid IS NULL OR sos_voterid = ''

                UNION ALL

                -- Deduplicate on sos_voterid + batch_id, prefer matched=TRUE, then lowest id
                SELECT DISTINCT ON (sos_voterid, batch_id) *
                FROM signatures
                WHERE sos_voterid IS NOT NULL AND sos_voterid <> ''
                ORDER BY sos_voterid, batch_id, matched DESC, id
            ) AS combined
        """)

        result = db.session.execute(sql, {"city_pattern": city_pattern}).fetchone()

        if not result:
            return {
                "entered": 0,
                "matched_target": 0,
                "matched_other": 0,
                "address_only_target": 0,
                "address_only_other": 0,
                "unmatched": 0,
                "percent_verified": 0,
                "percent_target": 0,
                "target_city": city_info["display"],
            }

        return {
            "entered": result.entered or 0,
            "matched_target": result.matched_target or 0,
            "matched_other": result.matched_other or 0,
            "address_only_target": result.address_only_target or 0,
            "address_only_other": result.address_only_other or 0,
            "unmatched": result.unmatched or 0,
            "percent_verified": result.percent_verified or 0,
            "percent_target": result.percent_target or 0,
            "target_city": city_info["display"],
        }

    @staticmethod
    def get_enterer_stats() -> list[dict]:
        """Get statistics per data enterer."""
        sql = text("""
            SELECT
                enterer_first || ' ' || enterer_last as name,
                count(distinct(book_number)) as books,
                count(distinct(sos_voterid)) as signatures
            FROM batches b
            LEFT JOIN signatures s ON b.id = s.batch_id
            GROUP BY 1
            ORDER BY 3 DESC
        """)

        result = db.session.execute(sql).fetchall()

        return [
            {"name": row.name, "books": row.books, "signatures": row.signatures}
            for row in result
        ]

    @staticmethod
    def get_book_stats(sort: str = "book_number", direction: str = "desc") -> list[dict]:
        """Get per-book signature counts and validity rates.

        sort: 'book_number' | 'entry_time'
        direction: 'asc' | 'desc'
        """
        # Build ORDER BY safely from a whitelist
        dir_sql = "DESC" if direction != "asc" else "ASC"
        nulls = "NULLS LAST" if dir_sql == "DESC" else "NULLS FIRST"

        if sort == "entry_time":
            order_clause = f"first_entry_at {dir_sql} {nulls}"
        else:
            # Numeric sort for all-digit book numbers, string fallback
            order_clause = (
                f"CASE WHEN b.book_number ~ '^\\d+$' THEN b.book_number::integer ELSE NULL END "
                f"{dir_sql} NULLS LAST, b.book_number {dir_sql}"
            )

        sql = text(f"""
            SELECT
                b.id,
                b.book_number,
                COALESCE(c.first_name || ' ' || c.last_name, 'Unknown') AS collector_name,
                b.date_out,
                b.date_back,
                MIN(bat.created_at) AS first_entry_at,
                COUNT(s.id) AS total_signatures,
                SUM(CASE WHEN s.matched IS TRUE THEN 1 ELSE 0 END) AS matched_count,
                ROUND(
                    SUM(CASE WHEN s.matched IS TRUE THEN 1 ELSE 0 END)
                    * 100.0 / NULLIF(COUNT(s.id), 0),
                    1
                ) AS validity_rate
            FROM books b
            LEFT JOIN collectors c ON b.collector_id = c.id
            LEFT JOIN signatures s ON s.book_id = b.id
            LEFT JOIN batches bat ON bat.book_id = b.id
            GROUP BY b.id, b.book_number, collector_name, b.date_out, b.date_back
            ORDER BY {order_clause}
        """)  # nosec — order_clause built from whitelist only

        rows = db.session.execute(sql).fetchall()

        return [
            {
                "id": row.id,
                "book_number": row.book_number,
                "collector_name": row.collector_name,
                "date_out": row.date_out,
                "date_back": row.date_back,
                "first_entry_at": row.first_entry_at,
                "total_signatures": row.total_signatures or 0,
                "matched_count": int(row.matched_count or 0),
                "validity_rate": float(row.validity_rate or 0),
            }
            for row in rows
        ]

    @staticmethod
    def get_organization_stats() -> list[dict]:
        """Get statistics per organization."""
        city_info = StatsService.get_target_city_info()
        city_pattern = city_info["pattern"]

        sql = text("""
            SELECT
                coalesce(o.name, 'Volunteers') as organization,
                count(distinct(b.id)) as books,
                sum(
                    case when s.matched is true
                    and s.registered_city like :city_pattern then 1 else 0 end
                ) as matched_target,
                sum(
                    case when s.matched is true
                    and (
                        s.registered_city not like :city_pattern or s.registered_city is null
                    ) then 1 else 0 end
                ) as matched_other,
                sum(
                    case when s.matched is false
                    and s.registered_city like :city_pattern then 1 else 0 end
                ) as address_only_target,
                sum(
                    case when s.matched is false
                    and (
                        s.registered_city not like :city_pattern or s.registered_city is null
                    )
                    and s.residential_zip <> '' then 1 else 0 end
                ) as address_only_other,
                sum(
                    case when s.residential_zip is null
                    or s.residential_zip = '' then 1 else 0 end
                ) as unmatched,
                round(
                    (
                        sum(
                            case when s.matched is true
                            and s.registered_city like :city_pattern then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_verified,
                round(
                    (
                        sum(
                            case when s.registered_city like :city_pattern then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_target
            FROM collectors c
            LEFT JOIN books b ON b.collector_id = c.id
            LEFT JOIN signatures s ON s.book_id = b.id
            LEFT JOIN organizations o ON c.organization_id = o.id
            GROUP BY 1
            ORDER BY 1 ASC
        """)

        result = db.session.execute(sql, {"city_pattern": city_pattern}).fetchall()

        return [
            {
                "organization": row.organization,
                "books": row.books or 0,
                "matched_target": row.matched_target or 0,
                "matched_other": row.matched_other or 0,
                "address_only_target": row.address_only_target or 0,
                "address_only_other": row.address_only_other or 0,
                "unmatched": row.unmatched or 0,
                "percent_verified": row.percent_verified or 0,
                "percent_target": row.percent_target or 0,
                "target_city": city_info["display"],
            }
            for row in result
        ]
