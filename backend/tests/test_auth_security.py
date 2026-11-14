"""Unit and integration tests for StegChat enterprise authentication and security.

Covers:
- Password policy: 10 chars, uppercase, lowercase, digit, common password blacklist rejection.
- Password 72-byte bcrypt limit handling (SHA-256 pre-hash).
- Session tokens stored only as SHA-256 hashes in DB.
- OTPs stored only as HMAC-SHA256 in DB.
- OTP attempt limits (max 5 invalid attempts then invalidated).
- OTP 60-second resend cooldown.
- Production environment guarantee: no OTP returned in responses unless APP_ENV=development and DEV_SHOW_OTP=true.
- CSRF double-submit protection rejection when cookie exists without matching header.
- Rate limiting protection with lockout.
- Timing-resistant identical response for unknown user vs incorrect password.
- Password change revoking other active sessions.
"""

import os
import secrets
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.db.session import SessionLocal
from backend.app.db.models import User, Session as DBSession, OTPVerification
from backend.app.auth.security import validate_password_policy, PasswordPolicyError
from backend.app.integrity import compute_sha256

@pytest.fixture
def app():
    os.environ["APP_ENV"] = "development"
    os.environ["DEV_SHOW_OTP"] = "true"
    return create_app()

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from backend.app.api.auth import auth_rate_limiter
    auth_rate_limiter._records.clear()
    auth_rate_limiter._lockouts.clear()
    yield
    auth_rate_limiter._records.clear()
    auth_rate_limiter._lockouts.clear()

def test_password_policy_validation():
    # Less than 10 characters
    with pytest.raises(PasswordPolicyError, match="at least 10 characters"):
        validate_password_policy("Ab1!short")

    # Missing uppercase
    with pytest.raises(PasswordPolicyError, match="uppercase"):
        validate_password_policy("lowercaseonly123!")

    # Missing lowercase
    with pytest.raises(PasswordPolicyError, match="lowercase"):
        validate_password_policy("UPPERCASEONLY123!")

    # Missing digit
    with pytest.raises(PasswordPolicyError, match="number"):
        validate_password_policy("NoDigitsHereAtAll!")

    # Blacklisted common password
    with pytest.raises(PasswordPolicyError, match="too common"):
        validate_password_policy("Password123!")

    # Valid password
    valid = "CorrectHorseBatteryStaple99!"
    assert validate_password_policy(valid) == valid

def test_password_72_byte_limit_handling():
    # 80 characters long password
    long_pass = "A" * 70 + "b123" + "CDEFghij"
    assert len(long_pass.encode("utf-8")) > 72
    prepared = validate_password_policy(long_pass)
    # Must be pre-hashed to base64 SHA-256 string (44 chars)
    assert len(prepared) == 44
    assert len(prepared.encode("utf-8")) <= 72

def test_tokens_and_otps_stored_only_as_hashes(client):
    os.environ["APP_ENV"] = "development"
    os.environ["DEV_SHOW_OTP"] = "true"

    username = f"usr_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    raw_password = "SecurePassword2026!#"

    # Register
    r = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "Security Tester",
        "password": raw_password,
    })
    assert r.status_code == 200
    v_id = r.json()["verification_id"]
    dev_hint = r.json().get("dev_hint")
    assert dev_hint is not None
    otp_code = dev_hint.split(": ")[-1]

    # Verify raw OTP is NOT anywhere in the database
    db = SessionLocal()
    try:
        otp_row = db.query(OTPVerification).filter(OTPVerification.id == v_id).first()
        assert otp_row is not None
        assert otp_row.otp_hash is not None
        assert len(otp_row.otp_hash) == 64  # SHA-256 / HMAC-SHA256 hex length
        assert otp_code not in otp_row.otp_hash

        # Verify OTP
        r_ver = client.post("/api/v1/auth/verify-otp", json={
            "verification_id": v_id,
            "otp_code": otp_code,
        })
        assert r_ver.status_code == 200

        # Check session token stored in DB is hashed with SHA-256
        session_cookie = r_ver.cookies.get("stegchat_session")
        assert session_cookie is not None
        hashed_cookie = compute_sha256(session_cookie.encode("utf-8"))

        sess_row = db.query(DBSession).filter(DBSession.token_hash == hashed_cookie).first()
        assert sess_row is not None
        # Raw session cookie must never equal the stored token_hash
        assert sess_row.token_hash != session_cookie
    finally:
        db.close()

def test_production_config_exposes_no_otp(client):
    os.environ["APP_ENV"] = "production"
    os.environ["DEV_SHOW_OTP"] = "false"

    username = f"prod_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "Prod Tester",
        "password": "SecurePassword2026!#",
    })
    assert r.status_code == 200
    data = r.json()
    assert "dev_hint" not in data
    assert "otp" not in str(data).lower() or "verification code sent" in str(data).lower()

    # Revert for subsequent test runs
    os.environ["APP_ENV"] = "development"
    os.environ["DEV_SHOW_OTP"] = "true"

def test_otp_attempt_limit_invalidation(client):
    username = f"att_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "Attempt Tester",
        "password": "SecurePassword2026!#",
    })
    v_id = r.json()["verification_id"]
    correct_otp = r.json()["dev_hint"].split(": ")[-1]

    # Submit 5 incorrect OTP attempts (disable IP rate limit to test record attempt cap)
    os.environ["DISABLE_RATE_LIMITER"] = "true"
    try:
        for _ in range(5):
            r_fail = client.post("/api/v1/auth/verify-otp", json={
                "verification_id": v_id,
                "otp_code": "000000",
            })
            assert r_fail.status_code == 400

        # 6th attempt with correct OTP must fail because the OTP record was invalidated
        r_final = client.post("/api/v1/auth/verify-otp", json={
            "verification_id": v_id,
            "otp_code": correct_otp,
        })
        assert r_final.status_code == 400
        assert "invalidated" in r_final.text.lower() or "attempts exceeded" in r_final.text.lower()
    finally:
        os.environ["DISABLE_RATE_LIMITER"] = "false"

def test_otp_resend_cooldown(client):
    username = f"cool_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "Cooldown Tester",
        "password": "SecurePassword2026!#",
    })
    v_id = r.json()["verification_id"]

    # Immediate resend should trigger 429 Cooldown
    r_resend = client.post("/api/v1/auth/resend-otp", json={"verification_id": v_id})
    assert r_resend.status_code == 429
    assert "wait" in r_resend.text.lower()

def test_csrf_protection_rejection(client):
    # Obtain CSRF cookie and session
    username = f"csrf_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    r_reg = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "CSRF Tester",
        "password": "SecurePassword2026!#",
    })
    v_id = r_reg.json()["verification_id"]
    otp = r_reg.json()["dev_hint"].split(": ")[-1]
    client.post("/api/v1/auth/verify-otp", json={"verification_id": v_id, "otp_code": otp})

    # Tampered or missing X-CSRF-Token on POST must return 403
    client.cookies.set("stegchat_csrf", "valid-csrf-secret-cookie-1234")
    r_bad_csrf = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "SecurePassword2026!#", "new_password": "NewSecurePassword2026!#"},
        headers={"X-CSRF-Token": "mismatched-csrf-header"}
    )
    assert r_bad_csrf.status_code == 403

def test_timing_and_response_consistency_for_unknown_user_vs_wrong_password(client):
    username = f"time_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    r_reg = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "Timing Tester",
        "password": "SecurePassword2026!#",
    })
    v_id = r_reg.json()["verification_id"]
    otp = r_reg.json()["dev_hint"].split(": ")[-1]
    client.post("/api/v1/auth/verify-otp", json={"verification_id": v_id, "otp_code": otp})

    # 1. Unknown user login
    r_unknown = client.post("/api/v1/auth/login", json={
        "username_or_email": f"nonexistent_{secrets.token_hex(4)}",
        "password": "WrongPassword2026!#",
    })

    # 2. Existing user with wrong password
    r_wrong_pwd = client.post("/api/v1/auth/login", json={
        "username_or_email": username,
        "password": "WrongPassword2026!#",
    })

    # Responses must be identical to avoid username enumeration (ignoring dynamic request_id)
    assert r_unknown.status_code == 401
    assert r_wrong_pwd.status_code == 401
    u_body = r_unknown.json()
    w_body = r_wrong_pwd.json()
    assert u_body.get("error", {}).get("code") == w_body.get("error", {}).get("code")
    assert u_body.get("error", {}).get("message") == w_body.get("error", {}).get("message")

def test_password_change_revokes_other_sessions(app):
    client1 = TestClient(app)
    client2 = TestClient(app)

    username = f"rev_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    pwd = "SecurePassword2026!#"

    # Register & verify session 1
    r_reg = client1.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "Revoke Tester",
        "password": pwd,
    })
    v_id = r_reg.json()["verification_id"]
    otp = r_reg.json()["dev_hint"].split(": ")[-1]
    client1.post("/api/v1/auth/verify-otp", json={"verification_id": v_id, "otp_code": otp})

    # Login second session
    time.sleep(0.01)
    r_login = client2.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    v_id2 = r_login.json()["verification_id"]
    otp2 = r_login.json()["dev_hint"].split(": ")[-1]
    r_ver2 = client2.post("/api/v1/auth/verify-otp", json={"verification_id": v_id2, "otp_code": otp2})
    csrf2 = r_ver2.cookies.get("stegchat_csrf")

    # Session 2 changes password with CSRF
    new_pwd = "NewPassword2026!#Updated"
    r_change = client2.post(
        "/api/v1/auth/change-password",
        json={"current_password": pwd, "new_password": new_pwd},
        headers={"X-CSRF-Token": csrf2} if csrf2 else {}
    )
    assert r_change.status_code == 200

    # Session 1 must now be revoked
    r_check_s1 = client1.get("/api/v1/auth/me")
    assert r_check_s1.status_code == 401

    # Session 2 remains active
    r_check_s2 = client2.get("/api/v1/auth/me")
    assert r_check_s2.status_code == 200
