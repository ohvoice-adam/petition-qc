from sqlalchemy import text

from app import db


class StatsService:
    """Service for calculating signature verification statistics."""

    @staticmethod
    def get_progress_stats() -> dict:
        """
        Get overall signature verification progress statistics.

        Returns dict with:
            - entered: Total signatures entered
            - matched_columbus: Matched signatures from Columbus residents
            - matched_not_columbus: Matched signatures from non-Columbus residents
            - matched_incorrect: Address-only matches from Columbus
            - matched_incorrect_not_columbus: Address-only matches from non-Columbus
            - unmatched: Signatures with no voter match
            - percent_verified: Percentage of verified Columbus signatures
            - percent_columbus: Percentage of all signatures from Columbus addresses
        """
        sql = text("""
            SELECT
                count(*) as entered,
                sum(
                    case when matched is true
                    and registered_city like 'COLUMBUS%' then 1 else 0 end
                ) as matched_columbus,
                sum(
                    case when matched is true
                    and (
                        registered_city not like 'COLUMBUS%' or registered_city is null
                    ) then 1 else 0 end
                ) as matched_not_columbus,
                sum(
                    case when matched is false
                    and registered_city like 'COLUMBUS%' then 1 else 0 end
                ) as matched_incorrect,
                sum(
                    case when matched is false
                    and (
                        registered_city not like 'COLUMBUS%' or registered_city is null
                    )
                    and residential_zip <> '' then 1 else 0 end
                ) as matched_incorrect_not_columbus,
                sum(
                    case when residential_zip is null
                    or residential_zip = '' then 1 else 0 end
                ) as unmatched,
                round(
                    (
                        sum(
                            case when matched is true
                            and registered_city like 'COLUMBUS%' then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_verified,
                round(
                    (
                        sum(
                            case when registered_city like 'COLUMBUS%' then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_columbus
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

        result = db.session.execute(sql).fetchone()

        if not result:
            return {
                "entered": 0,
                "matched_columbus": 0,
                "matched_not_columbus": 0,
                "matched_incorrect": 0,
                "matched_incorrect_not_columbus": 0,
                "unmatched": 0,
                "percent_verified": 0,
                "percent_columbus": 0,
            }

        return {
            "entered": result.entered or 0,
            "matched_columbus": result.matched_columbus or 0,
            "matched_not_columbus": result.matched_not_columbus or 0,
            "matched_incorrect": result.matched_incorrect or 0,
            "matched_incorrect_not_columbus": result.matched_incorrect_not_columbus or 0,
            "unmatched": result.unmatched or 0,
            "percent_verified": result.percent_verified or 0,
            "percent_columbus": result.percent_columbus or 0,
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
    def get_organization_stats() -> list[dict]:
        """Get statistics per organization."""
        sql = text("""
            SELECT
                coalesce(o.organization, 'Volunteers') as organization,
                count(distinct(b.id)) as books,
                sum(
                    case when s.matched is true
                    and s.registered_city like 'COLUMBUS%' then 1 else 0 end
                ) as matched_columbus,
                sum(
                    case when s.matched is true
                    and (
                        s.registered_city not like 'COLUMBUS%' or s.registered_city is null
                    ) then 1 else 0 end
                ) as matched_not_columbus,
                sum(
                    case when s.matched is false
                    and s.registered_city like 'COLUMBUS%' then 1 else 0 end
                ) as matched_incorrect,
                sum(
                    case when s.matched is false
                    and (
                        s.registered_city not like 'COLUMBUS%' or s.registered_city is null
                    )
                    and s.residential_zip <> '' then 1 else 0 end
                ) as matched_incorrect_not_columbus,
                sum(
                    case when s.residential_zip is null
                    or s.residential_zip = '' then 1 else 0 end
                ) as unmatched,
                round(
                    (
                        sum(
                            case when s.matched is true
                            and s.registered_city like 'COLUMBUS%' then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_verified,
                round(
                    (
                        sum(
                            case when s.registered_city like 'COLUMBUS%' then 1 else 0 end
                        ) * 100.0 / NULLIF(count(*), 0)
                    ), 0
                ) as percent_columbus
            FROM collectors c
            LEFT JOIN books b ON b.collector_id = c.id
            LEFT JOIN signatures s ON s.book_id = b.id
            LEFT JOIN paid_collectors p ON c.id = p.collector_id
            LEFT JOIN organizations o ON p.organization_id = o.id
            GROUP BY 1
            ORDER BY 1 ASC
        """)

        result = db.session.execute(sql).fetchall()

        return [
            {
                "organization": row.organization,
                "books": row.books or 0,
                "matched_columbus": row.matched_columbus or 0,
                "matched_not_columbus": row.matched_not_columbus or 0,
                "matched_incorrect": row.matched_incorrect or 0,
                "matched_incorrect_not_columbus": row.matched_incorrect_not_columbus or 0,
                "unmatched": row.unmatched or 0,
                "percent_verified": row.percent_verified or 0,
                "percent_columbus": row.percent_columbus or 0,
            }
            for row in result
        ]
