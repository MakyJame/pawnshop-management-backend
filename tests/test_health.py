from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_check_returns_healthy_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_database_health_check_returns_connected_status() -> None:
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
            "status": "healthy",
            "database": "connected",
    }
