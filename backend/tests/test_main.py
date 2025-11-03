"""
Tests for main FastAPI application endpoints.

Tests health checks and core application functionality.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_root_endpoint(test_client: TestClient):
    """Test root endpoint returns correct response."""
    response = test_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api"] == "GoingMerry-Stonks API"
    assert "message" in data


@pytest.mark.unit
def test_health_endpoint(test_client: TestClient):
    """Test health check endpoint."""
    response = test_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.smoke
def test_api_documentation_available(test_client: TestClient):
    """Test that API documentation is accessible."""
    # Test Swagger UI
    response = test_client.get("/api/docs")
    assert response.status_code == 200

    # Test ReDoc
    response = test_client.get("/api/redoc")
    assert response.status_code == 200


@pytest.mark.unit
def test_cors_headers(test_client: TestClient):
    """Test CORS headers are properly configured."""
    response = test_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


@pytest.mark.unit
def test_invalid_endpoint_returns_404(test_client: TestClient):
    """Test that invalid endpoints return 404."""
    response = test_client.get("/invalid/endpoint")
    assert response.status_code == 404
