import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.APP_NAME
    assert "timestamp" in data


def test_chat_get_status(client):
    response = client.get("/chat/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "chat router is ready"


def test_chat_post_message(client):
    response = client.post("/chat/", json={"message": "Hello AI"})
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Echo: Hello AI"
    assert data["status"] == "success"
