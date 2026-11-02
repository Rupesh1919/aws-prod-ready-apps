"""Data access layer for claims."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from claims_api.core.logging import get_logger
from claims_api.models.claim import Claim, ClaimStatus, ClaimType

logger = get_logger("repository")


class ConcurrencyError(Exception):
    """Raised when optimistic locking fails."""

    pass


class ClaimNotFoundError(Exception):
    """Raised when a claim is not found."""

    pass


class InvalidStatusTransitionError(Exception):
    """Raised when attempting an invalid status transition."""

    pass


class ClaimRepository:
    """Repository for claim data access."""

    def __init__(self, session: Session):
        """
        Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session

    def create(
        self,
        policy_reference: str,
        claim_type: ClaimType,
        description: str,
        claimed_amount: Decimal,
    ) -> Claim:
        """
        Create a new claim.
        
        Args:
            policy_reference: Policy reference number
            claim_type: Type of claim
            description: Claim description
            claimed_amount: Claimed amount
            
        Returns:
            Created claim
        """
        claim = Claim(
            policy_reference=policy_reference,
            claim_type=claim_type,
            description=description,
            claimed_amount=claimed_amount,
            status=ClaimStatus.SUBMITTED,
            version=1,
        )
        
        self.session.add(claim)
        self.session.flush()  # Get the ID without committing
        
        logger.info(
            f"Created claim {claim.id}",
            extra={"extra_fields": {"claim_id": str(claim.id), "policy": policy_reference}},
        )
        
        return claim

    def get_by_id(self, claim_id: uuid.UUID) -> Claim | None:
        """
        Get claim by ID.
        
        Args:
            claim_id: Claim ID
            
        Returns:
            Claim if found, None otherwise
        """
        stmt = select(Claim).where(Claim.id == claim_id)
        return self.session.scalar(stmt)

    def get_by_id_or_raise(self, claim_id: uuid.UUID) -> Claim:
        """
        Get claim by ID or raise exception.
        
        Args:
            claim_id: Claim ID
            
        Returns:
            Claim
            
        Raises:
            ClaimNotFoundError: If claim not found
        """
        claim = self.get_by_id(claim_id)
        if claim is None:
            raise ClaimNotFoundError(f"Claim {claim_id} not found")
        return claim

    def list_claims(
        self,
        offset: int = 0,
        limit: int = 20,
        status: ClaimStatus | None = None,
    ) -> tuple[list[Claim], int]:
        """
        List claims with pagination.
        
        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            Tuple of (claims list, total count)
        """
        # Build query
        stmt = select(Claim)
        if status is not None:
            stmt = stmt.where(Claim.status == status)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.scalar(count_stmt) or 0
        
        # Apply pagination and ordering
        stmt = stmt.order_by(Claim.created_at.desc()).offset(offset).limit(limit)
        
        claims = list(self.session.scalars(stmt).all())
        
        return claims, total

    def update_status(
        self,
        claim_id: uuid.UUID,
        new_status: ClaimStatus,
        expected_version: int,
    ) -> Claim:
        """
        Update claim status with optimistic locking.
        
        Args:
            claim_id: Claim ID
            new_status: New status
            expected_version: Expected version for optimistic locking
            
        Returns:
            Updated claim
            
        Raises:
            ClaimNotFoundError: If claim not found
            InvalidStatusTransitionError: If transition is not allowed
            ConcurrencyError: If version mismatch (concurrent update)
        """
        claim = self.get_by_id_or_raise(claim_id)
        
        # Check version for optimistic locking
        if claim.version != expected_version:
            logger.warning(
                f"Concurrency conflict updating claim {claim_id}: "
                f"expected version {expected_version}, found {claim.version}"
            )
            raise ConcurrencyError(
                f"Claim has been modified. Expected version {expected_version}, "
                f"found {claim.version}"
            )
        
        # Validate status transition
        if not claim.status.can_transition_to(new_status):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {claim.status.value} to {new_status.value}"
            )
        
        # Update status and increment version
        old_status = claim.status
        claim.status = new_status
        claim.version += 1
        
        self.session.flush()
        
        logger.info(
            f"Updated claim {claim_id} status from {old_status.value} to {new_status.value}",
            extra={
                "extra_fields": {
                    "claim_id": str(claim_id),
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "version": claim.version,
                }
            },
        )
        
        return claim
