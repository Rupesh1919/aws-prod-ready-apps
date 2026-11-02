"""Unit tests for data models."""

import pytest
from decimal import Decimal

from claims_api.models.claim import ClaimStatus, ClaimType
from claims_api.models.schemas import ClaimCreate, ClaimStatusUpdate


class TestClaimStatus:
    """Test ClaimStatus enum and transitions."""
    
    def test_valid_transitions(self):
        """Test valid status transitions."""
        assert ClaimStatus.SUBMITTED.can_transition_to(ClaimStatus.UNDER_REVIEW)
        assert ClaimStatus.UNDER_REVIEW.can_transition_to(ClaimStatus.APPROVED)
        assert ClaimStatus.APPROVED.can_transition_to(ClaimStatus.PAID)
        assert ClaimStatus.PAID.can_transition_to(ClaimStatus.CLOSED)
    
    def test_invalid_transitions(self):
        """Test invalid status transitions."""
        assert not ClaimStatus.SUBMITTED.can_transition_to(ClaimStatus.PAID)
        assert not ClaimStatus.APPROVED.can_transition_to(ClaimStatus.REJECTED)
        assert not ClaimStatus.CLOSED.can_transition_to(ClaimStatus.SUBMITTED)
    
    def test_closed_is_terminal(self):
        """Test that CLOSED status cannot transition anywhere."""
        for status in ClaimStatus:
            if status != ClaimStatus.CLOSED:
                assert not ClaimStatus.CLOSED.can_transition_to(status)


class TestClaimCreate:
    """Test ClaimCreate schema validation."""
    
    def test_valid_claim_data(self):
        """Test valid claim creation data."""
        data = {
            "policy_reference": "POL-2024-001",
            "claim_type": ClaimType.ACCIDENT,
            "description": "Valid claim description with sufficient length",
            "claimed_amount": Decimal("1000.50"),
        }
        claim = ClaimCreate(**data)
        assert claim.policy_reference == "POL-2024-001"
        assert claim.claimed_amount == Decimal("1000.50")
    
    def test_invalid_policy_reference(self):
        """Test policy reference validation."""
        with pytest.raises(ValueError):
            ClaimCreate(
                policy_reference="invalid policy!",  # Contains invalid characters
                claim_type=ClaimType.ACCIDENT,
                description="Valid description here",
                claimed_amount=Decimal("1000.00"),
            )
    
    def test_description_too_short(self):
        """Test description minimum length."""
        with pytest.raises(ValueError):
            ClaimCreate(
                policy_reference="POL-2024-001",
                claim_type=ClaimType.ACCIDENT,
                description="Short",  # Too short
                claimed_amount=Decimal("1000.00"),
            )
    
    def test_negative_amount(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(ValueError):
            ClaimCreate(
                policy_reference="POL-2024-001",
                claim_type=ClaimType.ACCIDENT,
                description="Valid description here",
                claimed_amount=Decimal("-100.00"),
            )
    
    def test_amount_precision(self):
        """Test that amounts are rounded to 2 decimal places."""
        claim = ClaimCreate(
            policy_reference="POL-2024-001",
            claim_type=ClaimType.ACCIDENT,
            description="Valid description here",
            claimed_amount=Decimal("1000.999"),
        )
        assert claim.claimed_amount == Decimal("1001.00")


class TestClaimStatusUpdate:
    """Test ClaimStatusUpdate schema."""
    
    def test_valid_status_update(self):
        """Test valid status update data."""
        update = ClaimStatusUpdate(
            status=ClaimStatus.APPROVED,
            version=1,
        )
        assert update.status == ClaimStatus.APPROVED
        assert update.version == 1
    
    def test_invalid_version(self):
        """Test that version must be positive."""
        with pytest.raises(ValueError):
            ClaimStatusUpdate(
                status=ClaimStatus.APPROVED,
                version=0,
            )
