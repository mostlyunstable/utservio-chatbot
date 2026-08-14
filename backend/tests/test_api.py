import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_chat_validation_missing_session():
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 422


def test_chat_validation_oversized_message():
    long_msg = "a" * 1500
    response = client.post(
        "/api/chat", json={"session_id": "test-123", "message": long_msg}
    )
    assert response.status_code == 422


def test_empty_history():
    sess_id = str(uuid.uuid4())
    response = client.get(f"/api/chat/{sess_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sess_id
    assert len(data["messages"]) == 0


def test_services_endpoint():
    response = client.get("/api/services")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
