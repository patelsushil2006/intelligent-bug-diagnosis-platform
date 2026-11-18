import os
import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config import Config
from app import create_app
from database.db import engine, init_db
from database.models import Base


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Use temporary test directory for uploads and vector store
    UPLOAD_FOLDER = PROJECT_ROOT / "uploads" / "test_uploads"
    VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store" / "test_data"
    LLM_PROVIDER = "offline"


@pytest.fixture(scope="session")
def app():
    """Create application instance for tests."""
    app = create_app(TestConfig)
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    with app.test_client() as test_client:
        with app.app_context():
            init_db()
        yield test_client
