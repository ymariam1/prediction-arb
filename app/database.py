from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# Create database engine
if "sqlite" in settings.database_url:
    engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL configuration - only import when needed
    try:
        import psycopg2
        engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True
        )
    except ImportError:
        # Fallback to SQLite if PostgreSQL dependencies aren't available
        print("Warning: PostgreSQL dependencies not available, falling back to SQLite")
        settings.database_url = "sqlite:///./prediction_arb.db"
        engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            connect_args={"check_same_thread": False}
        )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables in the database."""
    Base.metadata.drop_all(bind=engine)
