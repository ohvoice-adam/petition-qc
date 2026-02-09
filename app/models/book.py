from app import db


class Book(db.Model):
    """Petition books (collections of signature pages)."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    book_number = db.Column(db.String(50), nullable=False, index=True)
    collector_id = db.Column(db.Integer, db.ForeignKey("collectors.id"))
    date_out = db.Column(db.Date)
    date_back = db.Column(db.Date)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    collector = db.relationship("Collector", back_populates="books")
    batches = db.relationship("Batch", back_populates="book")
    signatures = db.relationship("Signature", back_populates="book")

    def __repr__(self):
        return f"<Book {self.book_number}>"
