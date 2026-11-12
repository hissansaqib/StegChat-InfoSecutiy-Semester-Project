"""
StegChat End-to-End Authentication Test
Tests the full registration -> OTP -> login -> session -> logout flow.
Uses a unique email to avoid conflicts with existing users.
"""
import sys
import json
import time
import uuid
import requests

BASE = "http://127.0.0.1:8000/api/v1"
UNIQUE = uuid.uuid4().hex[:8]
USERNAME = f"e2etest_{UNIQUE}"
EMAIL = f"e2etest_{UNIQUE}@example.com"
DISPLAY = "E2E Test User"
PASSWORD = "E2eTest_Secure1!"

session = requests.Session()
PASS = []
FAIL = []

def ok(name):
    PASS.append(name)
    print(f"  PASS: {name}")

def fail(name, reason):
    FAIL.append(name)
    print(f"  FAIL: {name} — {reason}")

print(f"\n=== StegChat E2E Auth Test  user={USERNAME} ===\n")

# ── 1. Health check ──────────────────────────────────────────────────────────
print("[1] Health check")
r = session.get(f"{BASE}/health")
if r.status_code == 200:
    ok("health endpoint responds 200")
else:
    fail("health endpoint", f"got {r.status_code}")

# ── 2. Register (initiate) ───────────────────────────────────────────────────
print("[2] Registration initiation")
r = session.post(f"{BASE}/auth/register", json={
    "username": USERNAME,
    "email": EMAIL,
    "display_name": DISPLAY,
    "password": PASSWORD,
})
if r.status_code != 200:
    fail("register initiation", f"status {r.status_code}: {r.text}")
    sys.exit(1)
body = r.json()
if body.get("status") != "mfa_required":
    fail("register returns mfa_required", f"got {body}")
    sys.exit(1)
ok("register initiation returns mfa_required")

verification_id = body.get("verification_id")
dev_hint = body.get("dev_hint", "")
if not verification_id:
    fail("verification_id present", "missing from response")
    sys.exit(1)
ok("verification_id present in response")

if not dev_hint:
    fail("dev_hint present", "DEV_SHOW_OTP may not be set correctly")
    sys.exit(1)
otp_code = dev_hint.split(":")[-1].strip()
ok(f"dev_hint present, OTP extracted: {otp_code}")

# ── 3. Duplicate registration (same email) ───────────────────────────────────
print("[3] Duplicate registration rejection")
r2 = session.post(f"{BASE}/auth/register", json={
    "username": f"other_{UNIQUE}",
    "email": EMAIL,
    "display_name": "Other",
    "password": PASSWORD,
})
if r2.status_code == 400:
    ok("duplicate email is rejected with 400")
else:
    fail("duplicate email rejection", f"got {r2.status_code}: {r2.text}")

# ── 4. Wrong OTP ─────────────────────────────────────────────────────────────
print("[4] Wrong OTP rejection")
r3 = session.post(f"{BASE}/auth/verify-otp", json={
    "verification_id": verification_id,
    "otp_code": "000000",
})
if r3.status_code == 400:
    ok("wrong OTP rejected with 400")
else:
    fail("wrong OTP rejection", f"got {r3.status_code}: {r3.text}")

# ── 5. Verify correct OTP → account creation ─────────────────────────────────
print("[5] OTP verification and account creation")
r4 = session.post(f"{BASE}/auth/verify-otp", json={
    "verification_id": verification_id,
    "otp_code": otp_code,
})
if r4.status_code != 200:
    fail("OTP verification", f"status {r4.status_code}: {r4.text}")
    sys.exit(1)
verify_body = r4.json()
if verify_body.get("status") != "success":
    fail("verify-otp returns success", f"got {verify_body}")
    sys.exit(1)
ok("OTP verified, account created")

user_obj = verify_body.get("user", {})
if user_obj.get("username") == USERNAME:
    ok(f"user object correct: username={USERNAME}")
else:
    fail("user object correct", f"got {user_obj}")

csrf_token = verify_body.get("csrf_token", "")
if csrf_token:
    ok("CSRF token issued")
else:
    fail("CSRF token", "not returned in verify-otp response")

# Update session CSRF header for further requests
session.headers.update({"X-CSRF-Token": csrf_token})

# ── 6. OTP reuse rejected ───────────────────────────────────────────────────
print("[6] OTP reuse prevention")
r5 = session.post(f"{BASE}/auth/verify-otp", json={
    "verification_id": verification_id,
    "otp_code": otp_code,
})
if r5.status_code == 400:
    ok("OTP reuse rejected with 400")
else:
    fail("OTP reuse rejected", f"got {r5.status_code}: {r5.text}")

# ── 7. /auth/me (session cookie set by verify-otp) ──────────────────────────
print("[7] Authenticated /auth/me")
r6 = session.get(f"{BASE}/auth/me")
if r6.status_code == 200:
    me = r6.json()
    if me.get("username") == USERNAME:
        ok("/auth/me returns correct user")
    else:
        fail("/auth/me user mismatch", str(me))
else:
    fail("/auth/me", f"status {r6.status_code}: {r6.text}")

# ── 8. Login (new OTP) ───────────────────────────────────────────────────────
print("[8] Login flow")
r7 = session.post(f"{BASE}/auth/login", json={
    "username_or_email": USERNAME,
    "password": PASSWORD,
})
if r7.status_code != 200:
    fail("login initiation", f"status {r7.status_code}: {r7.text}")
else:
    login_body = r7.json()
    if login_body.get("status") == "mfa_required":
        ok("login returns mfa_required")
        login_vid = login_body.get("verification_id")
        login_otp = login_body.get("dev_hint", "").split(":")[-1].strip()

        if login_otp:
            ok(f"login dev_hint OTP: {login_otp}")
            r8 = session.post(f"{BASE}/auth/verify-otp", json={
                "verification_id": login_vid,
                "otp_code": login_otp,
            })
            if r8.status_code == 200 and r8.json().get("status") == "success":
                ok("login OTP verified, session created")
                new_csrf = r8.json().get("csrf_token", "")
                session.headers.update({"X-CSRF-Token": new_csrf})
            else:
                fail("login OTP verify", f"{r8.status_code}: {r8.text}")
        else:
            fail("login dev_hint OTP", "not present")
    else:
        fail("login mfa_required", f"got {login_body}")

# ── 9. Logout ────────────────────────────────────────────────────────────────
print("[9] Logout")
r9 = session.post(f"{BASE}/auth/logout")
if r9.status_code == 200:
    ok("logout succeeded")
else:
    fail("logout", f"status {r9.status_code}: {r9.text}")

# ── 10. /auth/me after logout ────────────────────────────────────────────────
print("[10] /auth/me after logout (should be 401)")
r10 = session.get(f"{BASE}/auth/me")
if r10.status_code == 401:
    ok("session invalidated after logout")
else:
    fail("session invalidated", f"got {r10.status_code}: {r10.text}")

# ── 11. Wrong password login ─────────────────────────────────────────────────
print("[11] Wrong password rejected")
r11 = session.post(f"{BASE}/auth/login", json={
    "username_or_email": USERNAME,
    "password": "WrongPassword1!",
})
if r11.status_code == 401:
    ok("wrong password rejected with 401")
else:
    fail("wrong password rejection", f"got {r11.status_code}: {r11.text}")

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n=== RESULTS ===")
print(f"PASSED: {len(PASS)}")
print(f"FAILED: {len(FAIL)}")
if FAIL:
    print("FAILURES:")
    for f_name in FAIL:
        print(f"  - {f_name}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
