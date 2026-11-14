"""End-to-end full integration flow on an isolated temporary SQLite database."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import create_app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.carriers import get_carrier

@pytest.fixture(scope="module")
def temp_integration_client():
    # Create isolated temp database
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_e2e.db")
    engine = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    # Cleanup temp db
    engine.dispose()
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)
    os.rmdir(temp_dir)

def test_full_e2e_flow_temp_db(temp_integration_client: TestClient):
    client = temp_integration_client

    # 1. Register User Alice
    r_reg_a = client.post("/api/v1/auth/register", json={
        "username": "alice",
        "email": "alice@e2e.test",
        "display_name": "Alice Wonderland",
        "password": "Password1234!",
    })
    assert r_reg_a.status_code == 200, r_reg_a.text
    data_a = r_reg_a.json()
    assert data_a["status"] == "mfa_required"
    v_id_a = data_a["verification_id"]
    otp_a = data_a["dev_hint"].split(": ")[-1].strip()

    r_otp_a = client.post("/api/v1/auth/verify-otp", json={
        "verification_id": v_id_a,
        "otp_code": otp_a,
    })
    assert r_otp_a.status_code == 200
    assert r_otp_a.json()["user"]["username"] == "alice"

    # 2. Register User Bob
    r_reg_b = client.post("/api/v1/auth/register", json={
        "username": "bob",
        "email": "bob@e2e.test",
        "display_name": "Bob Builder",
        "password": "Password1234!",
    })
    assert r_reg_b.status_code == 200
    data_b = r_reg_b.json()
    v_id_b = data_b["verification_id"]
    otp_b = data_b["dev_hint"].split(": ")[-1].strip()

    r_otp_b = client.post("/api/v1/auth/verify-otp", json={
        "verification_id": v_id_b,
        "otp_code": otp_b,
    })
    assert r_otp_b.status_code == 200
    user_b_id = r_otp_b.json()["user"]["id"]

    # 3. Login as Alice
    r_login_a = client.post("/api/v1/auth/login", json={
        "username_or_email": "alice",
        "password": "Password1234!",
    })
    assert r_login_a.status_code == 200
    login_v_id_a = r_login_a.json()["verification_id"]
    login_otp_a = r_login_a.json()["dev_hint"].split(": ")[-1].strip()

    r_login_otp_a = client.post("/api/v1/auth/verify-otp", json={
        "verification_id": login_v_id_a,
        "otp_code": login_otp_a,
    })
    assert r_login_otp_a.status_code == 200
    user_a_id = r_login_otp_a.json()["user"]["id"]

    # 4. Upload Alice's cryptographic public key bundle
    fake_key_bundle = {
        "public_jwk": {"kty": "OKP", "crv": "X25519", "x": "test_public_key_base64"},
        "wrapped_private": "wrapped_priv_base64",
        "wrapped_nonce": "wrapped_nonce_base64",
        "salt": "salt_base64_16b",
        "kdf": {"id": "PBKDF2", "params": {"iterations": 100000}},
        "fingerprint": "fp_alice_001",
        "key_id": "master-v1",
    }
    r_key = client.put("/api/v1/keys/bundle", json=fake_key_bundle)
    assert r_key.status_code == 200

    # 5. Fetch Alice's own key bundle
    r_get_keys = client.get("/api/v1/keys/me")
    assert r_get_keys.status_code == 200
    assert r_get_keys.json()["fingerprint"] == "fp_alice_001"

    # 6. Create conversation between Alice and Bob
    r_conv = client.post("/api/v1/conversations", json={
        "participant_id": user_b_id,
        "title": "Alice & Bob Secure Channel",
    })
    assert r_conv.status_code == 200
    conv_id = r_conv.json()["id"]

    # 7. Alice sends a plaintext message
    r_msg_plain = client.post(f"/api/v1/conversations/{conv_id}/messages", json={
        "content": "Hello Bob, establishing covert channel.",
        "is_stego": False,
    })
    assert r_msg_plain.status_code == 200

    # 8. Alice sends a secret PNG stego message
    # Synthesize stego carrier in lab
    r_embed_png = client.post("/api/v1/lab/embed", json={
        "carrier_id": "png_lsb",
        "message": "Top secret meeting at 22:00 UTC",
        "algorithm": "aes-256-gcm",
        "passphrase": "alice-bob-shared-secret",
    })
    assert r_embed_png.status_code == 200
    png_stego_b64 = r_embed_png.json()["carrier_bytes"]

    r_msg_stego = client.post(f"/api/v1/conversations/{conv_id}/messages", json={
        "content": "[PNG Stego Image Attached]",
        "carrier_id": "png_lsb",
        "carrier_bytes": png_stego_b64,
        "is_stego": True,
    })
    assert r_msg_stego.status_code == 200

    # 9. List conversation messages and verify at-rest decryption
    r_msgs = client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert r_msgs.status_code == 200
    msgs = r_msgs.json()
    assert len(msgs) == 2
    assert msgs[0]["payload"]["text"] == "Hello Bob, establishing covert channel."
    assert msgs[1]["payload"]["carrier_id"] == "png_lsb"
    assert msgs[1]["payload"]["is_stego"] is True

    # 10. Reveal / extract secret message
    r_extract = client.post("/api/v1/lab/extract", json={
        "carrier_id": "png_lsb",
        "carrier_bytes": msgs[1]["payload"]["carrier_bytes"],
        "passphrase": "alice-bob-shared-secret",
    })
    assert r_extract.status_code == 200
    assert r_extract.json()["message"] == "Top secret meeting at 22:00 UTC"

    # 11. Run StegoBench benchmark suite
    r_bench = client.post("/api/v1/bench/run", json={
        "carrier_id": "png_lsb",
        "payload_size": 64,
        "iterations": 2,
        "algorithm": "chacha20-poly1305",
    })
    assert r_bench.status_code == 200
    assert r_bench.json()["status"] == "completed"
    assert r_bench.json()["recovery_rate"] == 1.0

    # 12. Run Steganalysis on the stego carrier
    r_analysis = client.post("/api/v1/analysis/run", json={
        "carrier_bytes": png_stego_b64,
        "carrier_id": "png_lsb",
    })
    assert r_analysis.status_code == 200
    assert "chi_square_stat" in r_analysis.json()

    # 13. Run Recommendation engine
    r_rec = client.post("/api/v1/recommend", json={"payload_bytes": 2048})
    assert r_rec.status_code == 200
    assert len(r_rec.json()["recommendations"]) > 0

    # 14. Run Hash & Integrity tools
    r_hash = client.post("/api/v1/integrity/hash", data={
        "text": "Forensic audit artifact string",
        "algorithms": "sha256",
    })
    assert r_hash.status_code == 200
    sha_val = r_hash.json()["digests"]["sha256"]["digest"] if isinstance(r_hash.json()["digests"]["sha256"], dict) else r_hash.json()["digests"]["sha256"]

    r_verify = client.post("/api/v1/integrity/verify", data={
        "text": "Forensic audit artifact string",
        "expected_digest": sha_val,
        "algorithm": "sha256",
    })
    assert r_verify.status_code == 200
    assert r_verify.json()["matches"] is True

    # 15. Create experiment report entry and list
    r_rep = client.post("/api/v1/reports/runs", json={
        "name": "E2E Final Report",
        "carrier_id": "png_lsb",
        "algorithm": "aes-256-gcm",
        "payload_size": 64,
        "recovery_rate": 1.0,
        "embed_time_ms": 12.4,
        "extract_time_ms": 10.2,
    })
    assert r_rep.status_code == 200
    report_id = r_rep.json()["id"]

    r_rep_get = client.get(f"/api/v1/reports/runs/{report_id}")
    assert r_rep_get.status_code == 200
    assert r_rep_get.json()["name"] == "E2E Final Report"

