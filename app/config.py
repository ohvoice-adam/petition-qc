import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://localhost:5432/petition_qc"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"connect_timeout": 5},
    }

    # Search settings
    SEARCH_RESULTS_LIMIT = 100  # Fewer results = faster response
    SEARCH_SIMILARITY_THRESHOLD = 0.2  # Lower = more results but faster

    # File upload settings
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/petition-qc-uploads")
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB max upload size
