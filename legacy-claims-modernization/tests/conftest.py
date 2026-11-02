"""Pytest configuration and fixtures."""

import os
from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from claims_api.core.config import Settings
from claims_api.db.repository import ClaimRepository
from claims_api.db.session import get_db
from claims_api.main import app
from claims_api.models.claim import Base, Claim, ClaimStatus, ClaimType


# Test database URL - uses separate test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://claims_user:claims_dev_password_CHANGE_IN_PRODUCTION@localhost:5432/claims_test_db"
)


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def repository(db_session: Session) -> ClaimRepository:
    """Create repository instance."""
    return ClaimRepository(db_session)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create test client with database dependency override."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_claim_data() -> dict:
    """Sample claim data for testing."""
    return {
        "policy_reference": "POL-2024-TEST001",
        "claim_type": ClaimType.ACCIDENT,
        "description": "Test claim description with sufficient length for validation",
        "claimed_amount": Decimal("1500.50"),
    }


@pytest.fixture
def created_claim(repository: ClaimRepository, sample_claim_data: dict) -> Claim:
    """Create a sample claim in the database."""
    return repository.create(**sample_claim_data)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Mock authentication headers for testing."""
    # In real tests with auth enabled, this would be a valid JWT
    return {"Authorization": "Bearer mock-token-for-testing"}
