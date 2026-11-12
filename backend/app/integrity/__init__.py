"""Integrity and hashing subsystem.

Components:
1. Password hashing: Argon2id with transparent bcrypt backward-compatibility & rehash.
2. Streaming digest service: SHA-256, SHA-512, SHA3-256, BLAKE2b (chunked streaming).
3. HMAC-SHA256 service with constant-time verification.
4. Constant-time digest comparison: `verify_digest(a, b)`.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import time
from typing import BinaryIO, Callable, Dict, List, Tuple, Any
import argon2
import bcrypt

# ---------------------------------------------------------------------------
# Argon2id & Bcrypt Password Hashing Service
# ---------------------------------------------------------------------------

_argon2_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    type=argon2.Type.ID,
)

def hash_password(password: str) -> str:
    """Hash password using modern Argon2id."""
    return _argon2_hasher.hash(password)

def verify_and_rehash_password(plain_password: str, hashed_password: str) -> Tuple[bool, bool, str | None]:
    """Verify password against either Argon2id or legacy bcrypt.
    
    Returns:
        (is_valid: bool, needs_rehash: bool, new_argon2_hash: str | None)
    """
    if hashed_password.startswith("$argon2"):
        try:
            is_valid = _argon2_hasher.verify(hashed_password, plain_password)
            needs_rehash = _argon2_hasher.check_needs_rehash(hashed_password)
            new_hash = hash_password(plain_password) if needs_rehash else None
            return True, needs_rehash, new_hash
        except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError):
            return False, False, None
        except Exception:
            return False, False, None

    # Fallback to legacy bcrypt
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            is_valid = bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            if is_valid:
                # Transparent upgrade: rehash to modern Argon2id
                new_hash = hash_password(plain_password)
                return True, True, new_hash
            return False, False, None
        except Exception:
            return False, False, None

    return False, False, None

# ---------------------------------------------------------------------------
# Streaming Digest Services
# ---------------------------------------------------------------------------

SUPPORTED_DIGEST_ALGORITHMS: Dict[str, Callable[[], hashlib._Hash]] = {
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512,
    "sha3_256": hashlib.sha3_256,
    "blake2b": hashlib.blake2b,
}

CHUNK_SIZE = 64 * 1024  # 64 KiB chunks for streaming file processing

def compute_stream_digest(
    stream: BinaryIO,
    algorithm: str = "sha256",
) -> Tuple[str, float]:
    """Compute hex digest of stream in 64 KiB chunks and return (hex_digest, duration_ms)."""
    clean_alg = algorithm.lower().replace("-", "_")
    if clean_alg not in SUPPORTED_DIGEST_ALGORITHMS:
        raise ValueError(f"Unsupported digest algorithm '{algorithm}'. Choose from {list(SUPPORTED_DIGEST_ALGORITHMS.keys())}")

    hasher = SUPPORTED_DIGEST_ALGORITHMS[clean_alg]()
    t0 = time.perf_counter()

    while chunk := stream.read(CHUNK_SIZE):
        hasher.update(chunk)

    duration_ms = (time.perf_counter() - t0) * 1000
    return hasher.hexdigest(), duration_ms

def compute_data_digests(
    data: bytes,
    algorithms: List[str] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Compute digests across one or more algorithms returning hex values and timings."""
    algs = algorithms or ["sha256", "sha512", "sha3_256", "blake2b"]
    results = {}

    for alg in algs:
        clean_alg = alg.lower().replace("-", "_")
        if clean_alg not in SUPPORTED_DIGEST_ALGORITHMS:
            continue
        stream = io.BytesIO(data)
        digest_hex, duration_ms = compute_stream_digest(stream, clean_alg)
        results[alg] = {
            "algorithm": alg,
            "digest": digest_hex,
            "duration_ms": round(duration_ms, 3),
            "byte_count": len(data),
        }

    return results

def compute_sha256(data: bytes) -> str:
    """Helper for instant standard SHA-256 hex string."""
    return hashlib.sha256(data).hexdigest()

def compute_hmac_sha256(key: bytes, data: bytes) -> str:
    """Compute HMAC-SHA256 hex digest using secret key."""
    return hmac.new(key, data, hashlib.sha256).hexdigest()

def verify_digest(expected: str, actual: str) -> bool:
    """Constant-time comparison of two hex digest strings preventing timing attacks."""
    return hmac.compare_digest(expected.strip().lower(), actual.strip().lower())

def verify_hmac(key: bytes, data: bytes, expected_hmac_hex: str) -> bool:
    """Constant-time verification of HMAC-SHA256."""
    actual_hmac = compute_hmac_sha256(key, data)
    return verify_digest(expected_hmac_hex, actual_hmac)

