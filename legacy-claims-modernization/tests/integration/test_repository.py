"""Integration tests for claim repository."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from claims_api.db.repository import (
    ClaimNotFoundError,
    ClaimRepository,
    ConcurrencyError,
    InvalidStatusTransitionError,
)
from claims_api.models.claim import Claim, ClaimStatus, ClaimType


@pytest.mark.integration
class TestClaimRepository:
    """Test ClaimRepository database operations."""
    
    def test_create_claim(self, repository: ClaimRepository, db_session: Session):
        """Test creating a claim."""
        claim = repository.create(
            policy_reference="POL-2024-TEST",
            claim_type=ClaimType.ACCIDENT,
            description="Test claim for integration testing purposes",
            claimed_amount=Decimal("1500.00"),
        )
        
        db_session.commit()
        
        assert claim.id is not None
        assert claim.status == ClaimStatus.SUBMITTED
        assert claim.version == 1
        assert claim.claimed_amount == Decimal("1500.00")
    
    def test_get_by_id(self, repository: ClaimRepository, created_claim: Claim):
        """Test retrieving a claim by ID."""
        claim = repository.get_by_id(created_claim.id)
        
        assert claim is not None
        assert claim.id == created_claim.id
        assert claim.policy_reference == created_claim.policy_reference
    
    def test_get_by_id_not_found(self, repository: ClaimRepository):
        """Test retrieving non-existent claim."""
        import uuid
        claim = repository.get_by_id(uuid.uuid4())
        
        assert claim is None
    
    def test_list_claims(self, repository: ClaimRepository, created_claim: Claim, db_session: Session):
        """Test listing claims with pagination."""
        # Create additional claims
        for i in range(5):
            repository.create(
                policy_reference=f"POL-2024-{i:04d}",
                claim_type=ClaimType.THEFT,
                description=f"Test claim number {i} with sufficient description",
                claimed_amount=Decimal("1000.00"),
            )
        db_session.commit()
        
        claims, total = repository.list_claims(offset=0, limit=3)
        
        assert len(claims) == 3
        assert total >= 6  # At least our created claims
        # Should be ordered by created_at desc (newest first)
        assert claims[0].created_at >= claims[1].created_at
    
    def test_update_status_success(self, repository: ClaimRepository, created_claim: Claim, db_session: Session):
        """Test updating claim status."""
        updated_claim = repository.update_status(
            claim_id=created_claim.id,
            new_status=ClaimStatus.UNDER_REVIEW,
            expected_version=1,
        )
        db_session.commit()
        
        assert updated_claim.status == ClaimStatus.UNDER_REVIEW
        assert updated_claim.version == 2
    
    def test_update_status_invalid_transition(self, repository: ClaimRepository, created_claim: Claim):
        """Test that invalid status transitions are rejected."""
        with pytest.raises(InvalidStatusTransitionError):
            repository.update_status(
                claim_id=created_claim.id,
                new_status=ClaimStatus.PAID,  # Cannot go directly from SUBMITTED to PAID
                expected_version=1,
            )
    
    def test_optimistic_locking(self, repository: ClaimRepository, created_claim: Claim, db_session: Session):
        """Test optimistic concurrency control."""
        # First update succeeds
        repository.update_status(
            claim_id=created_claim.id,
            new_status=ClaimStatus.UNDER_REVIEW,
            expected_version=1,
        )
        db_session.commit()
        
        # Second update with stale version fails
        with pytest.raises(ConcurrencyError):
            repository.update_status(
                claim_id=created_claim.id,
                new_status=ClaimStatus.APPROVED,
                expected_version=1,  # Stale version
            )
    
    def test_claim_not_found_error(self, repository: ClaimRepository):
        """Test ClaimNotFoundError is raised."""
        import uuid
        with pytest.raises(ClaimNotFoundError):
            repository.get_by_id_or_raise(uuid.uuid4())
