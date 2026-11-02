"""Claims API endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from claims_api.api.dependencies import AuthenticatedUser, Repository
from claims_api.core.logging import get_logger
from claims_api.db.repository import (
    ClaimNotFoundError,
    ConcurrencyError,
    InvalidStatusTransitionError,
)
from claims_api.models.schemas import (
    ClaimCreate,
    ClaimListResponse,
    ClaimResponse,
    ClaimStatusUpdate,
    ProblemDetail,
)

logger = get_logger("api.claims")

router = APIRouter(prefix="/api/claims", tags=["claims"])


@router.post(
    "",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ProblemDetail},
        401: {"model": ProblemDetail},
        500: {"model": ProblemDetail},
    },
)
def create_claim(
    claim_data: ClaimCreate,
    repository: Repository,
    user: AuthenticatedUser,
) -> ClaimResponse:
    """
    Create a new claim.
    
    Requires authentication. Creates a claim in SUBMITTED status.
    """
    try:
        logger.info(
            f"Creating claim for policy {claim_data.policy_reference}",
            extra={
                "extra_fields": {
                    "policy": claim_data.policy_reference,
                    "type": claim_data.claim_type.value,
                    "user": user.get("sub", "unknown"),
                }
            },
        )
        
        claim = repository.create(
            policy_reference=claim_data.policy_reference,
            claim_type=claim_data.claim_type,
            description=claim_data.description,
            claimed_amount=claim_data.claimed_amount,
        )
        
        return ClaimResponse.model_validate(claim)
        
    except SQLAlchemyError as e:
        logger.error(f"Database error creating claim: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create claim",
        )


@router.get(
    "/{claim_id}",
    response_model=ClaimResponse,
    responses={
        401: {"model": ProblemDetail},
        404: {"model": ProblemDetail},
        500: {"model": ProblemDetail},
    },
)
def get_claim(
    claim_id: uuid.UUID,
    repository: Repository,
    user: AuthenticatedUser,
) -> ClaimResponse:
    """
    Get a claim by ID.
    
    Requires authentication.
    """
    try:
        claim = repository.get_by_id(claim_id)
        
        if claim is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found",
            )
        
        return ClaimResponse.model_validate(claim)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving claim: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve claim",
        )


@router.get(
    "",
    response_model=ClaimListResponse,
    responses={
        401: {"model": ProblemDetail},
        500: {"model": ProblemDetail},
    },
)
def list_claims(
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    repository: Repository = None,
    user: AuthenticatedUser = None,
) -> ClaimListResponse:
    """
    List claims with pagination.
    
    Requires authentication. Returns claims ordered by creation date (newest first).
    """
    try:
        claims, total = repository.list_claims(offset=offset, limit=limit)
        
        return ClaimListResponse(
            claims=[ClaimResponse.model_validate(c) for c in claims],
            total=total,
            offset=offset,
            limit=limit,
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error listing claims: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list claims",
        )


@router.patch(
    "/{claim_id}/status",
    response_model=ClaimResponse,
    responses={
        400: {"model": ProblemDetail},
        401: {"model": ProblemDetail},
        404: {"model": ProblemDetail},
        409: {"model": ProblemDetail},
        500: {"model": ProblemDetail},
    },
)
def update_claim_status(
    claim_id: uuid.UUID,
    update_data: ClaimStatusUpdate,
    repository: Repository,
    user: AuthenticatedUser,
) -> ClaimResponse:
    """
    Update claim status with optimistic locking.
    
    Requires authentication. Only valid status transitions are allowed.
    Provide the current version number to prevent concurrent updates.
    """
    try:
        logger.info(
            f"Updating claim {claim_id} status to {update_data.status.value}",
            extra={
                "extra_fields": {
                    "claim_id": str(claim_id),
                    "new_status": update_data.status.value,
                    "version": update_data.version,
                    "user": user.get("sub", "unknown"),
                }
            },
        )
        
        claim = repository.update_status(
            claim_id=claim_id,
            new_status=update_data.status,
            expected_version=update_data.version,
        )
        
        return ClaimResponse.model_validate(claim)
        
    except ClaimNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found",
        )
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ConcurrencyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating claim status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update claim status",
        )
