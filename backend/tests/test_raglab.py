from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_does_not_expose_secret_values() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "configured_secret_names" in data
    assert "api" not in str(data).lower() or "GROQ_API_KEY" in data["configured_secret_names"]


def test_upload_and_chat_vertical_slice() -> None:
    files = {"file": ("raglab.md", b"# RAGLab\nRAGLab AI compares retrieval strategies and shows citations.", "text/markdown")}
    upload = client.post("/api/v1/documents", files=files)
    assert upload.status_code == 200
    document = upload.json()
    assert document["status"] == "indexed"
    assert document["chunk_count"] >= 1

    chat = client.post(
        "/api/v1/chat",
        json={"question": "What does RAGLab AI compare?", "strategy": "hybrid", "top_k": 3},
    )
    assert chat.status_code == 200
    data = chat.json()
    assert data["citations"]
    assert data["retrieved_chunks"]
    assert data["verdict"] in {"grounded", "insufficient_evidence"}

