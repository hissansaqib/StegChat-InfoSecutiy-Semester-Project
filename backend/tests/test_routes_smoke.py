"""Smoke tests for all OpenAPI endpoints.

Verifies that unauthenticated requests to protected endpoints return 401/403 (never 500),
public endpoints return 200, and malformed inputs return 400/422 (never 500).
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app

@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

def test_public_health_endpoints(client: TestClient):
    r1 = client.get("/api/v1/health")
    assert r1.status_code == 200
    assert r1.json().get("status") == "ok"

    r2 = client.get("/api/v1/healthz")
    assert r2.status_code == 200

def test_carriers_public_endpoints(client: TestClient):
    r = client.get("/api/v1/carriers")
    assert r.status_code == 200
    carriers = r.json()
    assert isinstance(carriers, list)
    carrier_ids = [c["id"] for c in carriers]
    assert "png_lsb" in carrier_ids
    assert "wav_lsb" in carrier_ids

def test_protected_endpoints_require_auth(client: TestClient):
    protected_gets = [
        "/api/v1/auth/me",
        "/api/v1/auth/sessions",
        "/api/v1/auth/activity",
        "/api/v1/users/me",
        "/api/v1/users",
        "/api/v1/conversations",
        "/api/v1/keys/me",
    ]
    for url in protected_gets:
        r = client.get(url)
        assert r.status_code in (401, 403), f"URL {url} returned {r.status_code} instead of 401/403"
        body = r.json()
        assert "error" in body or "detail" in body

def test_integrity_endpoints(client: TestClient):
    r = client.post("/api/v1/integrity/hash", data={"text": "StegChat Integrity Test", "algorithms": "sha256"})
    assert r.status_code == 200
    data = r.json()
    assert "digests" in data
    assert "sha256" in data["digests"]

    # Verify endpoint
    sha256_val = data["digests"]["sha256"]["digest"] if isinstance(data["digests"]["sha256"], dict) else data["digests"]["sha256"]
    r_ver = client.post("/api/v1/integrity/verify", data={"text": "StegChat Integrity Test", "expected_digest": sha256_val, "algorithm": "sha256"})
    assert r_ver.status_code == 200
    assert r_ver.json()["matches"] is True

    # Bad verify with empty fields returns 422 or 400, never 500
    r_bad = client.post("/api/v1/integrity/verify", json={})
    assert r_bad.status_code in (400, 422)

def test_recommendation_endpoint(client: TestClient):
    r = client.post("/api/v1/recommend", json={"payload_bytes": 1024})
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data

def test_lab_embed_and_extract_synthetic(client: TestClient):
    embed_req = {
        "carrier_id": "png_lsb",
        "message": "Top Secret Lab Embed Test",
        "algorithm": "aes-256-gcm",
        "passphrase": "lab-test-password-1234",
    }
    r = client.post("/api/v1/lab/embed", json=embed_req)
    assert r.status_code == 200, f"Lab embed failed: {r.text}"
    data = r.json()
    assert data["status"] == "success"
    carrier_bytes = data["carrier_bytes"]

    extract_req = {
        "carrier_id": "png_lsb",
        "carrier_bytes": carrier_bytes,
        "passphrase": "lab-test-password-1234",
    }
    r_extract = client.post("/api/v1/lab/extract", json=extract_req)
    assert r_extract.status_code == 200, f"Lab extract failed: {r_extract.text}"
    extract_data = r_extract.json()
    assert extract_data["status"] == "success"
    assert extract_data["message"] == "Top Secret Lab Embed Test"

def test_bench_suite_execution(client: TestClient):
    bench_req = {
        "carrier_id": "png_lsb",
        "payload_size": 32,
        "iterations": 2,
        "algorithm": "aes-256-gcm",
    }
    r = client.post("/api/v1/bench/run", json=bench_req)
    assert r.status_code == 200, f"Bench run failed: {r.text}"
    data = r.json()
    assert data["status"] == "completed"
    assert data["recovery_rate"] == 1.0
