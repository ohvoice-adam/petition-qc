from app import db


class Signature(db.Model):
    """Verified petition signatures."""

    __tablename__ = "signatures"

    id = db.Column(db.Integer, primary_key=True)

    # Voter identification
    sos_voterid = db.Column(db.String(20), index=True)
    county_number = db.Column(db.String(10))

    # Book and batch tracking
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))

    # Address info (copied from voter record at time of entry)
    residential_address1 = db.Column(db.String(255))
    residential_address2 = db.Column(db.String(100))
    residential_city = db.Column(db.String(100))
    residential_state = db.Column(db.String(2), default="OH")
    residential_zip = db.Column(db.String(10))

    # City from voter registration (may differ from residential)
    registered_city = db.Column(db.String(100))

    # Verification status
    matched = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    book = db.relationship("Book", back_populates="signatures")
    batch = db.relationship("Batch", back_populates="signatures")

    @property
    def is_target_city_resident(self):
        """Check if registered city matches the target city."""
        from app.models import Settings
        if self.registered_city:
            pattern = Settings.get_target_city_pattern().rstrip('%')
            return self.registered_city.upper().startswith(pattern)
        return False

    @property
    def has_address(self):
        """Check if we have address info (matched to a voter record)."""
        return bool(self.residential_zip)

    def __repr__(self):
        status = "matched" if self.matched else "unmatched"
        return f"<Signature {self.id} - {status}>"
