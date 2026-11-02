#!/usr/bin/env python3
"""Seed database with synthetic test data."""

import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from claims_api.core.logging import get_logger, setup_logging
from claims_api.db.session import get_db_context
from claims_api.models.claim import Claim, ClaimStatus, ClaimType

setup_logging()
logger = get_logger("seed")

# Synthetic seed data
SEED_DATA = [
    {
        "policy_reference": "POL-2024-001234",
        "claim_type": ClaimType.ACCIDENT,
        "description": "Vehicle collision on highway. Front bumper and headlight damage. Police report filed.",
        "claimed_amount": Decimal("3500.00"),
        "status": ClaimStatus.UNDER_REVIEW,
    },
    {
        "policy_reference": "POL-2024-002456",
        "claim_type": ClaimType.THEFT,
        "description": "Laptop stolen from vehicle parked at shopping center. Serial number ABC123XYZ.",
        "claimed_amount": Decimal("1200.00"),
        "status": ClaimStatus.APPROVED,
    },
    {
        "policy_reference": "POL-2024-003789",
        "claim_type": ClaimType.PROPERTY_DAMAGE,
        "description": "Water damage to home office due to pipe burst. Affecting carpet and furniture.",
        "claimed_amount": Decimal("5600.75"),
        "status": ClaimStatus.SUBMITTED,
    },
    {
        "policy_reference": "POL-2024-004321",
        "claim_type": ClaimType.LIABILITY,
        "description": "Customer injury on commercial property. Medical expenses and legal consultation required.",
        "claimed_amount": Decimal("12000.00"),
        "status": ClaimStatus.UNDER_REVIEW,
    },
    {
        "policy_reference": "POL-2024-005555",
        "claim_type": ClaimType.MEDICAL,
        "description": "Emergency room visit and follow-up treatment for workplace injury.",
        "claimed_amount": Decimal("2450.50"),
        "status": ClaimStatus.PAID,
    },
    {
        "policy_reference": "POL-2024-006789",
        "claim_type": ClaimType.ACCIDENT,
        "description": "Minor rear-end collision in parking lot. Rear bumper and tail light replacement needed.",
        "claimed_amount": Decimal("1800.00"),
        "status": ClaimStatus.REJECTED,
    },
    {
        "policy_reference": "POL-2024-007890",
        "claim_type": ClaimType.OTHER,
        "description": "Personal liability claim for accidental damage to neighbor's fence.",
        "claimed_amount": Decimal("850.25"),
        "status": ClaimStatus.CLOSED,
    },
    {
        "policy_reference": "POL-2024-008901",
        "claim_type": ClaimType.PROPERTY_DAMAGE,
        "description": "Storm damage to roof and siding. Multiple shingles missing and water intrusion.",
        "claimed_amount": Decimal("8900.00"),
        "status": ClaimStatus.SUBMITTED,
    },
]


def seed_database() -> None:
    """Seed the database with synthetic claims data."""
    try:
        logger.info(f"Starting database seed with {len(SEED_DATA)} claims")
        
        with get_db_context() as session:
            # Check if data already exists
            existing_count = session.query(Claim).count()
            
            if existing_count > 0:
                logger.info(f"Database already contains {existing_count} claims")
                response = input("Do you want to add more synthetic data? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Seed operation cancelled")
                    return
            
            # Insert seed data
            for data in SEED_DATA:
                claim = Claim(**data)
                session.add(claim)
            
            session.commit()
            
            logger.info(f"Successfully seeded {len(SEED_DATA)} claims")
            
            # Show summary
            total_claims = session.query(Claim).count()
            logger.info(f"Database now contains {total_claims} total claims")
            
    except Exception as e:
        logger.error(f"Seed operation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    seed_database()
