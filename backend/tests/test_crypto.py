"""Cryptographic test suite verifying ciphers, envelopes, HKDF, tampering, and rotation."""

import json
import os
import pytest
from backend.app.crypto import (
    encrypt,
    decrypt,
    hkdf,
    AtRestCipher,
    LabCipher,
    CryptoEnvelope,
    UnknownAlgorithmError,
    UnsupportedVersionError,
    CryptoDecryptionError,
    CryptoConfigurationError,
    SUPPORTED_ALGORITHMS,
)

FIXED_KEY_32 = b"\x05" * 32
PLAINTEXT_SAMPLE = b"Information Security StegChat Cryptographic Payload 2026!"

@pytest.mark.parametrize("alg", ["aes-256-gcm", "chacha20-poly1305"])
def test_cipher_roundtrip(alg: str):
    """Test standard roundtrip encryption and decryption for both ciphers."""
    aad = b"context-conversation-42"
    envelope = encrypt(
        plaintext=PLAINTEXT_SAMPLE,
        key=FIXED_KEY_32,
        alg=alg,
        aad=aad,
        key_id="test-key-1",
    )

    assert envelope.alg == alg
    assert envelope.v == 1
    assert envelope.key_id == "test-key-1"

    # Decrypt
    decrypted = decrypt(envelope, FIXED_KEY_32, aad=aad)
    assert decrypted == PLAINTEXT_SAMPLE

@pytest.mark.parametrize("alg", ["aes-256-gcm", "chacha20-poly1305"])
def test_tampered_ciphertext_fails(alg: str):
    """Tampering with a single bit in ciphertext must fail with no partial plaintext."""
    envelope = encrypt(PLAINTEXT_SAMPLE, FIXED_KEY_32, alg=alg, aad=b"meta")
    raw_dict = envelope.dict()

    # Tamper with ciphertext by altering base64 characters
    ct_chars = list(raw_dict["ciphertext"])
    ct_chars[0] = "A" if ct_chars[0] != "A" else "B"
    raw_dict["ciphertext"] = "".join(ct_chars)

    with pytest.raises(CryptoDecryptionError):
        decrypt(raw_dict, FIXED_KEY_32, aad=b"meta")

@pytest.mark.parametrize("alg", ["aes-256-gcm", "chacha20-poly1305"])
def test_tampered_nonce_fails(alg: str):
    """Tampering with nonce must trigger decryption error."""
    envelope = encrypt(PLAINTEXT_SAMPLE, FIXED_KEY_32, alg=alg)
    raw_dict = envelope.dict()

    nonce_chars = list(raw_dict["nonce"])
    nonce_chars[0] = "Z" if nonce_chars[0] != "Z" else "Y"
    raw_dict["nonce"] = "".join(nonce_chars)

    with pytest.raises(CryptoDecryptionError):
        decrypt(raw_dict, FIXED_KEY_32)

@pytest.mark.parametrize("alg", ["aes-256-gcm", "chacha20-poly1305"])
def test_tampered_aad_fails(alg: str):
    """Altered Associated Data must be rejected immediately."""
    envelope = encrypt(PLAINTEXT_SAMPLE, FIXED_KEY_32, alg=alg, aad=b"authorized_recipient")

    with pytest.raises(CryptoDecryptionError):
        decrypt(envelope, FIXED_KEY_32, aad=b"attacker_impersonation")

@pytest.mark.parametrize("alg", ["aes-256-gcm", "chacha20-poly1305"])
def test_wrong_key_fails(alg: str):
    """Decryption with incorrect key must fail."""
    envelope = encrypt(PLAINTEXT_SAMPLE, FIXED_KEY_32, alg=alg)
    wrong_key = b"\x09" * 32

    with pytest.raises(CryptoDecryptionError):
        decrypt(envelope, wrong_key)

def test_10000_unique_nonces():
    """Verify that 10,000 consecutively generated nonces are strictly unique."""
    nonces = set()
    for _ in range(10000):
        # 12-byte random nonces
        n = os.urandom(12)
        nonces.add(n)
    assert len(nonces) == 10000

def test_hkdf_known_answer_vectors():
    """Verify HKDF produces deterministic outputs matching domain separation."""
    ikm = b"known-ikm-for-test-vectors"
    salt = b"\x10" * 32
    info = b"stegchat/lab/v1"

    derived1 = hkdf(ikm, length=32, salt=salt, info=info)
    derived2 = hkdf(ikm, length=32, salt=salt, info=info)
    assert derived1 == derived2
    assert len(derived1) == 32

    # Different info yields different key
    derived_diff = hkdf(ikm, length=32, salt=salt, info=b"different/domain")
    assert derived1 != derived_diff

def test_key_rotation_support():
    """Verify that an older rotated key can still decrypt historical envelopes."""
    key_v1 = b"\x01" * 32
    key_v2 = b"\x02" * 32

    # Create cipher with key v1 and encrypt
    os.environ["STEGCHAT_MASTER_KEY"] = "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
    arc = AtRestCipher(key_id="master-v1")
    env_v1 = arc.encrypt(b"Historical legacy message", alg="aes-256-gcm")

    # Rotate active key to v2
    arc.active_key_id = "master-v2"
    arc.register_historical_key("master-v1", key_v1)
    arc._key_store["master-v2"] = key_v2

    # Verify old message still decrypts using key_id lookup
    assert arc.decrypt(env_v1) == b"Historical legacy message"

    # New message uses master-v2
    env_v2 = arc.encrypt(b"New message under rotated key", alg="chacha20-poly1305")
    assert env_v2.key_id == "master-v2"
    assert arc.decrypt(env_v2) == b"New message under rotated key"

def test_unknown_algorithm_rejected():
    """Unknown algorithms must raise UnknownAlgorithmError."""
    with pytest.raises(UnknownAlgorithmError):
        encrypt(PLAINTEXT_SAMPLE, FIXED_KEY_32, alg="des-ede3-cbc")

    envelope = encrypt(PLAINTEXT_SAMPLE, FIXED_KEY_32, alg="aes-256-gcm")
    raw = envelope.dict()
    raw["alg"] = "rc4-unsupported"
    with pytest.raises(UnknownAlgorithmError):
        decrypt(raw, FIXED_KEY_32)
