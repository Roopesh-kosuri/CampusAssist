"""Integration tests for CampusAssist FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["retrievers_loaded"] is True


def test_get_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "thresholds" in data
    assert "hyb" in data["thresholds"]
    assert "emb" in data["thresholds"]
    assert len(data["methods"]) >= 4
    assert "Hostel" in data["categories"]


def test_serve_index_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CampusAssist" in response.text


def test_query_in_scope_success(client):
    payload = {
        "query": "How do I register a hostel maintenance complaint?",
        "method": "hyb",
        "category": "Hostel",
        "polish": False
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is False
    assert data["confidence"] >= data["threshold"]
    assert data["matched_faq"] is not None
    assert data["matched_faq"]["id"] == "hos_01"
    assert data["answer_original"] is not None
    assert len(data["top3"]) == 3
    assert data["latency_ms"] >= 0.0
    assert "query_id" in data


def test_query_out_of_scope_fallback(client):
    payload = {
        "query": "How do I build a nuclear fusion reactor on Mars?",
        "method": "hyb",
        "category": "All",
        "polish": False
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["matched_faq"] is None
    assert data["answer_original"] is None
    assert data["answer_polished"] is None
    assert "department_contact" in data
    assert len(data["department_contact"]) > 5


def test_query_pii_redaction(client):
    payload = {
        "query": "My registration number is 12015843 and phone +91 9876543210 where to submit fees?",
        "method": "hyb",
        "category": "Fees",
        "polish": False
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Query must still succeed, but PII was scrubbed
    assert "query_id" in data


def test_query_guardrails(client):
    # Empty query
    res_empty = client.post("/api/query", json={"query": "   ", "method": "hyb"})
    assert res_empty.status_code == 400

    # Overly long query (> 300 chars)
    long_query = "When does the library close? " * 20
    assert len(long_query) > 300
    res_long = client.post("/api/query", json={"query": long_query, "method": "hyb"})
    assert res_long.status_code in (400, 422)


def test_feedback_flow(client):
    # First submit a query
    res = client.post("/api/query", json={"query": "Where is central library?", "method": "hyb"})
    assert res.status_code == 200
    qid = res.json()["query_id"]

    # Submit helpful feedback
    res_fb = client.post("/api/feedback", json={"query_id": qid, "helpful": True})
    assert res_fb.status_code == 200
    assert res_fb.json()["status"] == "ok"

    # Non-existent query ID
    res_bad = client.post("/api/feedback", json={"query_id": 999999, "helpful": False})
    assert res_bad.status_code == 404


def test_get_analytics(client):
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_queries"] >= 1
    assert "fallback_rate" in data
    assert "avg_confidence" in data
    assert "helpful_percent" in data
    assert "by_category" in data


def test_get_evaluation(client):
    response = client.get("/api/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert "methods" in data
    assert "split" in data
    assert "thresholds_used" in data
