"""Database session management and dependency injection."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import Pool

from claims_api.core.config import Settings, get_settings
from claims_api.core.logging import get_logger

logger = get_logger("database")

# Global engine and session factory
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_database_url(settings: Settings) -> str:
    """Get database URL with SSL mode."""
    url = settings.database_url
    if settings.database_ssl_mode and settings.database_ssl_mode != "disable":
        url = f"{url}?sslmode={settings.database_ssl_mode}"
    return url


def create_database_engine(settings: Settings) -> Engine:
    """
    Create SQLAlchemy engine with connection pooling.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured engine
    """
    database_url = get_database_url(settings)
    
    # Create engine with connection pool
    engine = create_engine(
        database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,  # Set to True for SQL debugging
    )
    
    # Log pool events
    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn: object, connection_record: object) -> None:
        logger.debug("Database connection opened")
    
    @event.listens_for(Pool, "checkout")
    def receive_checkout(
        dbapi_conn: object, connection_record: object, connection_proxy: object
    ) -> None:
        logger.debug("Database connection checked out from pool")
    
    return engine


def init_db(settings: Settings | None = None) -> None:
    """
    Initialize database engine and session factory.
    
    Args:
        settings: Application settings (uses default if not provided)
    """
    global _engine, _session_factory
    
    if settings is None:
        settings = get_settings()
    
    logger.info(
        f"Initializing database connection: "
        f"{settings.database_host}:{settings.database_port}/{settings.database_name}"
    )
    
    _engine = create_database_engine(settings)
    _session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    
    logger.info("Database initialized successfully")


def get_engine() -> Engine:
    """Get the database engine."""
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get the session factory."""
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup.
    
    Yields:
        Database session
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database sessions.
    
    Yields:
        Database session with automatic cleanup
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db() -> None:
    """Close database connections and dispose of the engine."""
    global _engine, _session_factory
    
    if _engine is not None:
        logger.info("Closing database connections")
        _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")
