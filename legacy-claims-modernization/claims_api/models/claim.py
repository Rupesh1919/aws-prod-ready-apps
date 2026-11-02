"""Claim database model."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DECIMAL, CheckConstraint, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class ClaimStatus(str, enum.Enum):
    """Allowed claim statuses with valid transitions."""

    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"
    CLOSED = "CLOSED"

    @classmethod
    def valid_transitions(cls) -> dict[str, list[str]]:
        """
        Define valid status transitions.
        
        Returns:
            Dictionary mapping current status to allowed next statuses
        """
        return {
            cls.SUBMITTED.value: [cls.UNDER_REVIEW.value, cls.REJECTED.value],
            cls.UNDER_REVIEW.value: [cls.APPROVED.value, cls.REJECTED.value],
            cls.APPROVED.value: [cls.PAID.value],
            cls.REJECTED.value: [cls.CLOSED.value],
            cls.PAID.value: [cls.CLOSED.value],
            cls.CLOSED.value: [],  # Terminal state
        }

    def can_transition_to(self, new_status: "ClaimStatus") -> bool:
        """
        Check if transition to new status is valid.
        
        Args:
            new_status: Target status
            
        Returns:
            True if transition is allowed
        """
        allowed = self.valid_transitions().get(self.value, [])
        return new_status.value in allowed


class ClaimType(str, enum.Enum):
    """Types of insurance claims."""

    ACCIDENT = "ACCIDENT"
    THEFT = "THEFT"
    PROPERTY_DAMAGE = "PROPERTY_DAMAGE"
    LIABILITY = "LIABILITY"
    MEDICAL = "MEDICAL"
    OTHER = "OTHER"


class Claim(Base):
    """Claim database model."""

    __tablename__ = "claims"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Core fields
    policy_reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    claim_type: Mapped[ClaimType] = mapped_column(
        Enum(ClaimType, name="claim_type_enum"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    claimed_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=12, scale=2),
        nullable=False,
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status_enum"),
        nullable=False,
        default=ClaimStatus.SUBMITTED,
        index=True,
    )

    # Timestamps - always UTC
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Optimistic concurrency control
    version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")

    # Constraints
    __table_args__ = (
        CheckConstraint("claimed_amount >= 0", name="claimed_amount_non_negative"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(description) <= 2000", name="description_max_length"),
        CheckConstraint("length(policy_reference) >= 1", name="policy_reference_not_empty"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Claim(id={self.id}, policy={self.policy_reference}, "
            f"type={self.claim_type.value}, status={self.status.value}, "
            f"amount={self.claimed_amount})>"
        )
