from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

# PostgreSQL with connection pooling for concurrent access
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,          # Number of connections to keep open
    max_overflow=20,       # Extra connections allowed during high load
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=300       # Recycle connections after 5 minutes
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass
