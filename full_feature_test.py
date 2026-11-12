import sys
import json
import uuid
import requests

BASE = "http://127.0.0.1:8000/api/v1"
session = requests.Session()

def test_flow():
    # 1. Health
    r = session.get(f"{BASE}/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("Health OK")

    # 2. Register
    uid = uuid.uuid4().hex[:6]
    username = f"u_{uid}"
    email = f"u_{uid}@test.com"
    reg_data = {
        "username": username,
        "email": email,
        "display_name": f"User {uid}",
        "password": "SecurePassword123!"
    }
    r = session.post(f"{BASE}/auth/register", json=reg_data)
    assert r.status_code == 200, f"Register failed: {r.text}"
    resp = r.json()
    vid = resp["verification_id"]
    otp = resp["dev_hint"].split(":")[-1].strip()
    print("Register initiated, OTP:", otp)

    # 3. Verify OTP
    r = session.post(f"{BASE}/auth/verify-otp", json={"verification_id": vid, "otp_code": otp})
    assert r.status_code == 200, f"Verify OTP failed: {r.text}"
    user_data = r.json()
    csrf_token = user_data["csrf_token"]
    session.headers.update({"X-CSRF-Token": csrf_token})
    print("User registered and logged in:", user_data["user"]["username"])

    # 4. Carriers list
    r = session.get(f"{BASE}/carriers")
    assert r.status_code == 200, f"Carriers list failed: {r.text}"
    carriers = r.json()
    print("Carriers available:", carriers)

    # 5. Lab embed
    r = session.post(f"{BASE}/lab/embed", json={"carrier_id": "fake", "message": "Secret message from test"})
    assert r.status_code == 200, f"Lab embed failed: {r.text}"
    embed_res = r.json()
    carrier_bytes = embed_res["carrier_bytes"]
    print("Lab embed OK, bytes length:", len(carrier_bytes))

    # 6. Lab extract
    r = session.post(f"{BASE}/lab/extract", json={"carrier_id": "fake", "carrier_bytes": carrier_bytes})
    assert r.status_code == 200, f"Lab extract failed: {r.text}"
    extract_res = r.json()
    assert extract_res["message"] == "Secret message from test", f"Extraction mismatch: {extract_res}"
    print("Lab extract OK, recovered message:", extract_res["message"])

    # 7. StegoBench Run
    r = session.post(f"{BASE}/bench/run", json={"carrier_id": "fake", "payload_size": 32, "iterations": 2})
    assert r.status_code == 200, f"Bench run failed: {r.text}"
    bench_res = r.json()
    print("Bench run OK:", bench_res["name"], "Recovery:", bench_res["recovery_rate"])

    # 8. Analysis
    r = session.post(f"{BASE}/analysis/run", json={"carrier_id": "fake", "carrier_bytes": carrier_bytes})
    assert r.status_code == 200, f"Analysis run failed: {r.text}"
    analysis_res = r.json()
    print("Analysis OK, stego detected:", analysis_res["stego_detected"])

    # 9. Recommendation
    r = session.post(f"{BASE}/recommend", json={"payload_bytes": 100})
    assert r.status_code == 200, f"Recommend failed: {r.text}"
    recs = r.json()
    print("Recommendations returned:", len(recs["recommendations"]))

    # 10. Reports Run list
    r = session.get(f"{BASE}/reports/runs")
    assert r.status_code == 200, f"Reports runs failed: {r.text}"
    print("Reports runs returned:", len(r.json()))

    # 11. Conversation creation & Message sending
    r = session.post(f"{BASE}/conversations", json={"title": "Test Chat"})
    assert r.status_code == 200, f"Create conversation failed: {r.text}"
    conv_id = r.json()["id"]
    print("Created conversation:", conv_id)

    # Send plain message
    r = session.post(f"{BASE}/conversations/{conv_id}/messages", json={"content": "Hello World!"})
    assert r.status_code == 200, f"Send message failed: {r.text}"
    print("Sent plain message OK")

    # Send stego message
    r = session.post(f"{BASE}/conversations/{conv_id}/messages", json={
        "content": "[Stego Image]",
        "carrier_id": "fake",
        "carrier_bytes": carrier_bytes,
        "is_stego": True
    })
    assert r.status_code == 200, f"Send stego message failed: {r.text}"
    print("Sent stego message OK")

    # List messages
    r = session.get(f"{BASE}/conversations/{conv_id}/messages")
    assert r.status_code == 200, f"List messages failed: {r.text}"
    msgs = r.json()
    assert len(msgs) == 2, f"Expected 2 messages, got {len(msgs)}"
    print("Listed messages OK, count:", len(msgs))

    print("\nALL FEATURE ENDPOINTS VERIFIED & WORKING!")

if __name__ == "__main__":
    test_flow()
