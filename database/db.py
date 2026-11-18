from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config.config import Config
from database.models import Base

# Create SQLAlchemy engine
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False} if "sqlite" in Config.SQLALCHEMY_DATABASE_URI else {},
    echo=False
)

# Thread-safe session factory
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
SessionLocal = scoped_session(session_factory)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
