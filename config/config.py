import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Central application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-bug-diagnosis-2026")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

    # Storage Paths
    BASE_DIR = BASE_DIR
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    VECTOR_STORE_DIR = BASE_DIR / "vector_store" / "data"
    KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base" / "datasets"

    # Database
    DATABASE_PATH = BASE_DIR / "bug_platform.db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security & Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit
    ALLOWED_EXTENSIONS = {"txt", "log", "json", "csv", "py", "java", "js", "ts", "cpp", "c"}

    # RAG & Embedding Settings
    EMBEDDING_MODEL_NAME = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
    )
    TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "5"))

    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "offline")  # 'offline', 'gemini', 'openai'
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")


# Ensure necessary local storage directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.VECTOR_STORE_DIR, exist_ok=True)
os.makedirs(Config.KNOWLEDGE_BASE_DIR, exist_ok=True)
