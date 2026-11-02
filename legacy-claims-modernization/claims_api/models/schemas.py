"""Pydantic schemas for API request/response validation."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from claims_api.models.claim import ClaimStatus, ClaimType


class ClaimCreate(BaseModel):
    """Schema for creating a new claim."""

    policy_reference: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            pattern=r"^[A-Z0-9\-]+$",
            description="Policy reference (alphanumeric and hyphens only)",
            examples=["POL-2024-001234"],
        ),
    ]
    claim_type: Annotated[
        ClaimType,
        Field(description="Type of claim"),
    ]
    description: Annotated[
        str,
        Field(
            min_length=10,
            max_length=2000,
            description="Detailed description of the claim",
        ),
    ]
    claimed_amount: Annotated[
        Decimal,
        Field(
            gt=0,
            decimal_places=2,
            description="Claimed amount in currency units",
            examples=[1500.50],
        ),
    ]

    @field_validator("claimed_amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate claimed amount."""
        if v <= 0:
            raise ValueError("claimed_amount must be positive")
        if v >= Decimal("10000000000"):  # 10 billion limit
            raise ValueError("claimed_amount exceeds maximum allowed")
        return v.quantize(Decimal("0.01"))


class ClaimStatusUpdate(BaseModel):
    """Schema for updating claim status with optimistic concurrency."""

    status: Annotated[
        ClaimStatus,
        Field(description="New status for the claim"),
    ]
    version: Annotated[
        int,
        Field(
            ge=1,
            description="Current version number for optimistic locking",
        ),
    ]


class ClaimResponse(BaseModel):
    """Schema for claim response."""

    id: uuid.UUID
    policy_reference: str
    claim_type: ClaimType
    description: str
    claimed_amount: Decimal
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
        },
    }


class PaginationParams(BaseModel):
    """Pagination parameters."""

    offset: Annotated[
        int,
        Field(
            ge=0,
            description="Number of records to skip",
            examples=[0],
        ),
    ] = 0
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=100,
            description="Maximum number of records to return",
            examples=[20],
        ),
    ] = 20


class ClaimListResponse(BaseModel):
    """Schema for paginated list of claims."""

    claims: list[ClaimResponse]
    total: Annotated[
        int,
        Field(description="Total number of claims matching the query"),
    ]
    offset: Annotated[
        int,
        Field(description="Current offset"),
    ]
    limit: Annotated[
        int,
        Field(description="Current limit"),
    ]


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""

    type: str = Field(default="about:blank")
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None

    model_config = {"extra": "allow"}
