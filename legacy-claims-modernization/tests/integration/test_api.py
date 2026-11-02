"""Integration tests for API endpoints."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from claims_api.models.claim import Claim, ClaimStatus, ClaimType


@pytest.mark.integration
class TestClaimsAPI:
    """Test Claims API endpoints end-to-end."""
    
    def test_health_endpoints(self, client: TestClient):
        """Test health check endpoints."""
        # Liveness
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
        
        # Readiness
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        assert "database" in response.json()
    
    def test_create_claim_success(self, client: TestClient, auth_headers: dict):
        """Test successful claim creation."""
        claim_data = {
            "policy_reference": "POL-2024-API-TEST",
            "claim_type": "ACCIDENT",
            "description": "Integration test claim with sufficient detail for validation",
            "claimed_amount": 2500.50,
        }
        
        response = client.post("/api/claims", json=claim_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["policy_reference"] == claim_data["policy_reference"]
        assert data["status"] == "SUBMITTED"
        assert data["version"] == 1
        assert "id" in data
    
    def test_create_claim_validation_error(self, client: TestClient, auth_headers: dict):
        """Test claim creation with invalid data."""
        invalid_data = {
            "policy_reference": "INVALID!@#",  # Invalid characters
            "claim_type": "ACCIDENT",
            "description": "Short",  # Too short
            "claimed_amount": -100,  # Negative
        }
        
        response = client.post("/api/claims", json=invalid_data, headers=auth_headers)
        assert response.status_code == 400
    
    def test_get_claim_success(self, client: TestClient, created_claim: Claim, auth_headers: dict):
        """Test retrieving a claim."""
        response = client.get(f"/api/claims/{created_claim.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(created_claim.id)
        assert data["policy_reference"] == created_claim.policy_reference
    
    def test_get_claim_not_found(self, client: TestClient, auth_headers: dict):
        """Test retrieving non-existent claim."""
        import uuid
        fake_id = uuid.uuid4()
        
        response = client.get(f"/api/claims/{fake_id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_list_claims(self, client: TestClient, created_claim: Claim, auth_headers: dict):
        """Test listing claims with pagination."""
        response = client.get("/api/claims?offset=0&limit=10", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["claims"]) >= 1
    
    def test_update_claim_status_success(
        self, client: TestClient, created_claim: Claim, auth_headers: dict
    ):
        """Test updating claim status."""
        update_data = {
            "status": "UNDER_REVIEW",
            "version": 1,
        }
        
        response = client.patch(
            f"/api/claims/{created_claim.id}/status",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UNDER_REVIEW"
        assert data["version"] == 2
    
    def test_update_claim_status_invalid_transition(
        self, client: TestClient, created_claim: Claim, auth_headers: dict
    ):
        """Test invalid status transition."""
        update_data = {
            "status": "PAID",  # Cannot go directly from SUBMITTED to PAID
            "version": 1,
        }
        
        response = client.patch(
            f"/api/claims/{created_claim.id}/status",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 400
        assert "transition" in response.json()["detail"].lower()
    
    def test_update_claim_status_concurrency_error(
        self, client: TestClient, created_claim: Claim, auth_headers: dict
    ):
        """Test optimistic locking with stale version."""
        # First update
        update_data = {"status": "UNDER_REVIEW", "version": 1}
        response = client.patch(
            f"/api/claims/{created_claim.id}/status",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        # Second update with stale version
        update_data = {"status": "APPROVED", "version": 1}  # Stale version
        response = client.patch(
            f"/api/claims/{created_claim.id}/status",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 409
        assert "version" in response.json()["detail"].lower()
    
    def test_end_to_end_claim_workflow(
        self, client: TestClient, auth_headers: dict, db_session: Session
    ):
        """Test complete claim lifecycle."""
        # 1. Create claim
        claim_data = {
            "policy_reference": "POL-2024-E2E",
            "claim_type": "MEDICAL",
            "description": "End-to-end test claim for complete workflow validation",
            "claimed_amount": 5000.00,
        }
        response = client.post("/api/claims", json=claim_data, headers=auth_headers)
        assert response.status_code == 201
        claim_id = response.json()["id"]
        
        # 2. Retrieve claim
        response = client.get(f"/api/claims/{claim_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "SUBMITTED"
        
        # 3. Move to UNDER_REVIEW
        response = client.patch(
            f"/api/claims/{claim_id}/status",
            json={"status": "UNDER_REVIEW", "version": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["version"] == 2
        
        # 4. Approve claim
        response = client.patch(
            f"/api/claims/{claim_id}/status",
            json={"status": "APPROVED", "version": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"
        
        # 5. Mark as paid
        response = client.patch(
            f"/api/claims/{claim_id}/status",
            json={"status": "PAID", "version": 3},
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        # 6. Close claim
        response = client.patch(
            f"/api/claims/{claim_id}/status",
            json={"status": "CLOSED", "version": 4},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CLOSED"
        assert response.json()["version"] == 5
        
        # 7. Verify claim is in list
        response = client.get("/api/claims?offset=0&limit=10", headers=auth_headers)
        assert response.status_code == 200
        claims = response.json()["claims"]
        assert any(c["id"] == claim_id for c in claims)
