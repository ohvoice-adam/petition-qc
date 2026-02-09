from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

from app.config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.signatures import bp as signatures_bp
    from app.routes.collectors import bp as collectors_bp
    from app.routes.stats import bp as stats_bp
    from app.routes.auth import bp as auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(signatures_bp, url_prefix="/signatures")
    app.register_blueprint(collectors_bp, url_prefix="/collectors")
    app.register_blueprint(stats_bp, url_prefix="/stats")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Create tables and enable pg_trgm
    with app.app_context():
        from app.models import User, Voter, Signature, Book, Batch, Collector, DataEnterer
        db.create_all()

        # Enable pg_trgm extension
        try:
            db.session.execute(db.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    return app
