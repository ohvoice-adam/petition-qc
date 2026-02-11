from app import db


class Settings(db.Model):
    """Application settings stored in the database."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    @classmethod
    def get(cls, key: str, default: str = None) -> str:
        """Get a setting value by key."""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key: str, value: str) -> None:
        """Set a setting value."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

    @classmethod
    def get_target_city(cls) -> str:
        """Get the target city for signature verification."""
        return cls.get("target_city", "COLUMBUS CITY")

    @classmethod
    def get_target_city_display(cls) -> str:
        """Get the target city in title case for display."""
        city = cls.get_target_city()
        return city.title() if city else "Columbus"

    @classmethod
    def get_target_city_pattern(cls) -> str:
        """Get the SQL LIKE pattern for matching the target city."""
        city = cls.get_target_city()
        if city:
            # Remove " CITY" suffix for pattern matching if present
            base = city.replace(" CITY", "").replace(" city", "")
            return f"{base}%"
        return "COLUMBUS%"

    @classmethod
    def get_signature_goal(cls) -> int:
        """Get the signature goal count."""
        value = cls.get("signature_goal")
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    @classmethod
    def set_signature_goal(cls, goal: int) -> None:
        """Set the signature goal count."""
        cls.set("signature_goal", str(goal))

    def __repr__(self):
        return f"<Settings {self.key}={self.value}>"
