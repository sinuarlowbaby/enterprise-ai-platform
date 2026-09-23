"""Automated tests for FastAPI app, health endpoint, chat router, and lifespan."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    # TestClient as a context manager triggers FastAPI lifespan (startup and shutdown)
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    """Verify /health returns 200 OK and valid JSON structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.APP_NAME
    assert "timestamp" in data


def test_chat_status(client):
    """Verify /chat/status endpoint."""
    response = client.get("/chat/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "chat"


def test_chat_message_post(client):
    """Verify /chat POST endpoint accepts query and returns structured reply."""
    payload = {
        "message": "Hello, is the Enterprise AI system online?",
        "conversation_id": "test-conv-123",
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == "test-conv-123"
    assert "Echo / Acknowledged" in data["reply"]
    assert data["status"] == "success"


def test_chat_message_validation_failure(client):
    """Verify invalid payloads to /chat fail validation with 422."""
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422
