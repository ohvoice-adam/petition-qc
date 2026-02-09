from app import db


class Voter(db.Model):
    """Franklin County Voter File - used for signature verification."""

    __tablename__ = "voters"

    id = db.Column(db.Integer, primary_key=True)
    sos_voterid = db.Column(db.String(20), index=True)
    county_id = db.Column(db.String(20))

    first_name = db.Column(db.String(100))
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))

    residential_address1 = db.Column(db.String(255))
    residential_address2 = db.Column(db.String(100))
    residential_city = db.Column(db.String(100))
    residential_state = db.Column(db.String(2), default="OH")
    residential_zip = db.Column(db.String(10))

    # City field (may differ from residential_city for unincorporated areas)
    city = db.Column(db.String(100))

    date_of_birth = db.Column(db.Date)
    registration_date = db.Column(db.Date)

    precinct_code = db.Column(db.String(50))
    precinct_name = db.Column(db.String(200))
    ward = db.Column(db.String(200))

    __table_args__ = (
        # B-tree index for fast prefix search (ILIKE 'xxx%')
        db.Index("idx_voters_address_btree", residential_address1),
        # Trigram index for fuzzy address search
        db.Index(
            "idx_voters_address_trgm",
            residential_address1,
            postgresql_using="gin",
            postgresql_ops={"residential_address1": "gin_trgm_ops"},
        ),
        # Trigram index for name search
        db.Index(
            "idx_voters_name_trgm",
            last_name,
            postgresql_using="gin",
            postgresql_ops={"last_name": "gin_trgm_ops"},
        ),
    )

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)

    @property
    def full_address(self):
        parts = [self.residential_address1]
        if self.residential_address2:
            parts.append(self.residential_address2)
        parts.append(f"{self.residential_city}, {self.residential_state} {self.residential_zip}")
        return ", ".join(parts)

    def __repr__(self):
        return f"<Voter {self.sos_voterid}: {self.full_name}>"
