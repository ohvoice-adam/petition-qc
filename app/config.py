import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://localhost:5432/petition_qc"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Search settings
    SEARCH_RESULTS_LIMIT = 100  # Fewer results = faster response
    SEARCH_SIMILARITY_THRESHOLD = 0.2  # Lower = more results but faster
