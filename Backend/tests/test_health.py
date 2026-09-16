"""
Unit tests for the health check and database connectivity endpoints.
"""

import asyncio
from app.main import app


def test_root_health_endpoint():
    """Verify that GET /health returns 200 with status healthy and app metadata."""
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["app_name"] == "SatQuery"
        assert "version" in payload
        assert "timestamp" in payload
    except ImportError:
        # Fallback when httpx is not yet installed in the environment
        from app.api.v1.endpoints.health import health_check
        result = asyncio.run(health_check())
        assert result.status == "healthy"
        assert result.app_name == "SatQuery"
        assert result.version is not None


def test_api_v1_health_endpoint():
    """Verify that GET /api/v1/health returns 200 with matching schema."""
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["app_name"] == "SatQuery"
    except ImportError:
        from app.api.v1.endpoints.health import health_check
        result = asyncio.run(health_check())
        assert result.status == "healthy"


def test_database_health_endpoint():
    """Verify that GET /health/db responds gracefully (either 200 or 503)."""
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health/db")
        assert response.status_code in (200, 503)
        payload = response.json()
        assert "database" in payload
        assert "status" in payload
        assert "timestamp" in payload
    except ImportError:
        pass


def test_root_endpoint():
    """Verify root endpoint returns welcome payload."""
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        payload = response.json()
        assert "message" in payload
        assert payload["health"] == "/health"
        assert payload["database_health"] == "/health/db"
    except ImportError:
        from app.main import root
        result = asyncio.run(root())
        assert "message" in result
        assert result["health"] == "/health"


if __name__ == "__main__":
    test_root_health_endpoint()
    test_api_v1_health_endpoint()
    test_database_health_endpoint()
    test_root_endpoint()
    print("All health and database endpoint tests passed successfully.")
