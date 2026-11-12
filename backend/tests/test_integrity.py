"""Tests for backend/app/integrity subsystem.

Verifies:
1. Known-answer vectors for every algorithm (empty string and 'abc').
2. HMAC RFC 4231 test vectors.
3. Streaming equals one-shot hashing.
4. Tampered attachment fails download verification.
5. Argon2id login and bcrypt-to-Argon2 transparent rehash.
"""

import io
import os
import pytest
import bcrypt
from fastapi.testclient import TestClient

from backend.app.integrity import (
    hash_password,
    verify_and_rehash_password,
    compute_data_digests,
    compute_stream_digest,
    compute_sha256,
    compute_hmac_sha256,
    verify_digest,
    verify_hmac,
)
from backend.app.main import create_app
from backend.app.db.session import SessionLocal
from backend.app.db.models import User, Attachment, Conversation, ConversationMember

# ---------------------------------------------------------------------------
# 1. Known-Answer Vectors for empty string and 'abc'
# ---------------------------------------------------------------------------

KNOWN_VECTORS = {
    b"": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha512": "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e",
        "sha3_256": "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a",
        "blake2b": "786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f5419d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce",
    },
    b"abc": {
        "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "sha512": "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f",
        "sha3_256": "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532",
        "blake2b": "ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d17d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923",
    },
}

@pytest.mark.parametrize("sample,expected_dict", KNOWN_VECTORS.items())
def test_known_answer_digests(sample: bytes, expected_dict: dict):
    digests = compute_data_digests(sample, list(expected_dict.keys()))
    for alg, expected_hex in expected_dict.items():
        actual_hex = digests[alg]["digest"]
        assert actual_hex == expected_hex, f"Mismatch for {alg} on {sample}: expected {expected_hex}, got {actual_hex}"
        assert verify_digest(expected_hex, actual_hex) is True

# ---------------------------------------------------------------------------
# 2. HMAC RFC 4231 Test Vectors
# ---------------------------------------------------------------------------

def test_hmac_rfc4231_test_case_1():
    # RFC 4231 Test Case 1: Key = 20 bytes 0x0b, Data = "Hi There"
    key = b"\x0b" * 20
    data = b"Hi There"
    expected = "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
    actual = compute_hmac_sha256(key, data)
    assert actual == expected
    assert verify_hmac(key, data, expected) is True

def test_hmac_rfc4231_test_case_2():
    # RFC 4231 Test Case 2: Key = "Jefe", Data = "what do ya want for nothing?"
    key = b"Jefe"
    data = b"what do ya want for nothing?"
    expected = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
    actual = compute_hmac_sha256(key, data)
    assert actual == expected
    assert verify_hmac(key, data, expected) is True

# ---------------------------------------------------------------------------
# 3. Streaming Equals One-Shot Hashing
# ---------------------------------------------------------------------------

def test_streaming_equals_oneshot():
    # Large 256 KiB buffer exceeding 64 KiB chunk boundary
    large_data = b"A" * (256 * 1024)
    for alg in ["sha256", "sha512", "sha3_256", "blake2b"]:
        oneshot_hex = compute_data_digests(large_data, [alg])[alg]["digest"]
        stream_hex, _ = compute_stream_digest(io.BytesIO(large_data), alg)
        assert oneshot_hex == stream_hex

# ---------------------------------------------------------------------------
# 4. Argon2id and Legacy Bcrypt Transparent Rehash
# ---------------------------------------------------------------------------

def test_argon2id_hashing_and_rehash():
    password = "SuperStrongPassword2026!"
    argon_hash = hash_password(password)
    assert argon_hash.startswith("$argon2id$")

    valid, rehash, _ = verify_and_rehash_password(password, argon_hash)
    assert valid is True
    assert rehash is False

    # Legacy bcrypt verification and transparent rehash
    old_bcrypt = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    valid, rehash, new_hash = verify_and_rehash_password(password, old_bcrypt)
    assert valid is True
    assert rehash is True
    assert new_hash.startswith("$argon2id$")

    # Wrong password fails
    valid, _, _ = verify_and_rehash_password("WrongPassword!", argon_hash)
    assert valid is False

# ---------------------------------------------------------------------------
# 5. Tampered Attachment Fails Download Verification (HTTP 422)
# ---------------------------------------------------------------------------

def test_tampered_attachment_fails_download_integrity():
    app = create_app()
    client = TestClient(app)

    # 1. Register & verify user
    os.environ["DEV_SHOW_OTP"] = "true"
    username = f"user_{os.urandom(4).hex()}"
    email = f"{username}@test.com"
    r_reg = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "Test User",
        "password": "SecurePassword2026!#"
    })
    v_id = r_reg.json()["verification_id"]
    otp = r_reg.json()["dev_hint"].split(": ")[-1]
    client.post("/api/v1/auth/verify-otp", json={"verification_id": v_id, "otp_code": otp})

    # 2. Create conversation
    r_conv = client.post("/api/v1/conversations", json={"title": "Attachment Integrity Test"})
    conv_id = r_conv.json()["id"]

    # 3. Upload valid text attachment
    original_content = b"Integrity verified document content 2026."
    r_up = client.post(
        f"/api/v1/conversations/{conv_id}/attachments",
        files={"file": ("report.txt", original_content, "text/plain")},
    )
    assert r_up.status_code == 200
    att_id = r_up.json()["id"]
    expected_sha256 = r_up.json()["sha256"]
    assert expected_sha256 == compute_sha256(original_content)

    # 4. Successful download before tampering
    r_down = client.get(f"/api/v1/attachments/{att_id}")
    assert r_down.status_code == 200
    assert r_down.content == original_content

    # 5. Tamper file directly on disk
    db = SessionLocal()
    att_record = db.query(Attachment).filter(Attachment.id == att_id).first()
    disk_path = att_record.storage_path
    db.close()

    with open(disk_path, "wb") as f:
        f.write(b"TAMPERED CORRUPTED CONTENT BY ATTACKER")

    # 6. Subsequent download MUST fail with 422 Integrity Error
    r_tampered = client.get(f"/api/v1/attachments/{att_id}")
    assert r_tampered.status_code == 422
    assert "INTEGRITY ERROR" in r_tampered.json()["detail"]
